#!/usr/bin/env python3
"""
NucleiAI — Ollama integration for Nuclei pipeline
- Pre-scan:  suggest_tags()      — enrich Nuclei tags using bm12 scan context
- Pre-scan:  generate_templates() — generate custom YAML templates via Ollama
- Post-scan: analyze_findings()   — triage results with risk score + remediation
All methods fail silently if Ollama is unavailable or OLLAMA_ENABLED=false.
"""

import json
import logging
import os

import requests

log = logging.getLogger('nuclei-ai')

# Minimal Nuclei template example shown to the model to anchor format.
_TEMPLATE_EXAMPLE = """\
id: ai-gen-example-80
info:
  name: Example Service Detection
  author: ai-gen
  severity: info
  tags: ai-generated,example
http:
  - method: GET
    path:
      - "{{BaseURL}}"
    matchers:
      - type: word
        part: body
        words:
          - "Example"
"""

_TEMPLATE_SYSTEM = (
    'You are a Nuclei YAML template generator. Generate a single detection template '
    'for the service described by the user.\n\n'
    'REQUIRED FORMAT (follow exactly):\n'
    + _TEMPLATE_EXAMPLE +
    '\nRULES:\n'
    '- id: lowercase, hyphens only, must start with "ai-gen-"\n'
    '- severity: info (detection/fingerprint) or low/medium/high/critical (known vuln)\n'
    '- tags: always include "ai-generated" plus relevant product tag\n'
    '- path: use {{BaseURL}} — Nuclei injects the target URL automatically\n'
    '- matchers: word (string in body/header), status (HTTP code), regex (pattern)\n'
    '- Keep it simple: prefer passive detection over active exploitation\n'
    '- Return ONLY the YAML. No explanation, no markdown fences, no extra text.'
)


class NucleiAI:
    def __init__(self):
        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434').rstrip('/')
        self.model    = os.getenv('OLLAMA_MODEL', 'mistral:7b-instruct')
        self.enabled  = os.getenv('OLLAMA_ENABLED', 'false').lower() == 'true'
        self.timeout  = int(os.getenv('OLLAMA_TIMEOUT', '120'))

    def _call(self, system: str, user: str, max_tokens: int = 512,
              timeout: int = None) -> str | None:
        """POST to Ollama /v1/chat/completions. Returns content string or None."""
        try:
            resp = requests.post(
                f'{self.base_url}/v1/chat/completions',
                json={
                    'model': self.model,
                    'messages': [
                        {'role': 'system', 'content': system},
                        {'role': 'user',   'content': user},
                    ],
                    'max_tokens': max_tokens,
                    'temperature': 0.1,
                },
                timeout=timeout or self.timeout,
            )
            resp.raise_for_status()
            return resp.json()['choices'][0]['message']['content']
        except Exception as e:
            log.warning(f'Ollama call failed: {e}')
            return None

    def _strip_fences(self, text: str) -> str:
        """Remove markdown code fences if present."""
        s = text.strip()
        if s.startswith('```'):
            lines = s.split('\n')
            s = '\n'.join(lines[1:])
            if s.endswith('```'):
                s = s[:-3].strip()
        return s

    # ------------------------------------------------------------------
    # Post-scan: triage
    # ------------------------------------------------------------------

    def analyze_findings(self, ip: str, findings: list, severity_counts: dict) -> dict | None:
        """
        Triage Nuclei findings with Ollama.
        Returns dict with risk_score, risk_level, attack_surface, top_risks,
        remediation, reasoning — or None on any error.
        """
        if not self.enabled or not findings:
            return None

        capped = findings[:40]
        summary = [
            {
                'name':       f.get('info', {}).get('name', f.get('template-id', '')),
                'severity':   f.get('info', {}).get('severity', 'info'),
                'matched_at': f.get('matched-at', ''),
                'tags':       f.get('info', {}).get('tags', []),
            }
            for f in capped
        ]

        system = (
            'You are a security analyst. Analyze Nuclei scan findings and return a JSON object with:\n'
            '- risk_score: integer 0-100\n'
            '- risk_level: "critical"|"high"|"medium"|"low"|"info"\n'
            '- attack_surface: brief string describing exposed attack surface\n'
            '- top_risks: list of top 3 finding names\n'
            '- remediation: list of 3 concise remediation steps\n'
            '- reasoning: one sentence explaining the score\n'
            'Respond ONLY with valid JSON. No markdown, no explanation outside the JSON.'
        )
        user = json.dumps({
            'ip':              ip,
            'severity_counts': severity_counts,
            'findings':        summary,
        })

        content = self._call(system, user, max_tokens=600)
        if not content:
            return None

        try:
            result = json.loads(self._strip_fences(content))
            required = {'risk_score', 'risk_level', 'attack_surface', 'top_risks', 'remediation', 'reasoning'}
            missing = required - result.keys()
            if missing:
                log.warning(f'Ollama triage missing fields: {missing}')
                return None
            result['risk_score'] = max(0, min(100, int(result['risk_score'])))
            return result
        except Exception as e:
            log.warning(f'Ollama triage parse error: {e}')
            return None

    # ------------------------------------------------------------------
    # Pre-scan: tag enrichment
    # ------------------------------------------------------------------

    def suggest_tags(self, scan_details_raw, current_tags: str) -> str:
        """
        Enrich Nuclei tags based on bm12 scan context (OS, products, ports, banners).
        Returns merged sorted comma-separated tag string.
        Returns current_tags unchanged on any error.
        """
        if not self.enabled:
            return current_tags

        try:
            if isinstance(scan_details_raw, str):
                details = json.loads(scan_details_raw)
            else:
                details = scan_details_raw or {}

            context = {
                'os':           details.get('os', ''),
                'products':     details.get('products', []),
                'ports':        details.get('ports', []),
                'banners':      details.get('banners', {}),
                'current_tags': current_tags,
            }

            system = (
                'You are a security scanner expert. Based on the scan context, '
                'suggest additional Nuclei template tags.\n'
                'Return ONLY a JSON array of tag strings (max 12 total), '
                'e.g. ["apache","cve","default-login","exposed"].\n'
                'Use only valid Nuclei tag names. No markdown, no explanation.'
            )

            content = self._call(system, json.dumps(context), max_tokens=200)
            if not content:
                return current_tags

            ai_tags = json.loads(self._strip_fences(content))
            if not isinstance(ai_tags, list):
                return current_tags

            base   = {t.strip() for t in current_tags.split(',') if t.strip()}
            merged = base | {str(t).strip().lower() for t in ai_tags if t}
            result = ','.join(sorted(merged))
            log.info(f'AI tags: {current_tags} → {result}')
            return result

        except Exception as e:
            log.warning(f'suggest_tags failed: {e}')
            return current_tags

    # ------------------------------------------------------------------
    # Pre-scan: custom template generation
    # ------------------------------------------------------------------

    def _validate_template(self, yaml_str: str) -> bool:
        """Structural validation of a Nuclei template YAML."""
        try:
            import yaml
            t = yaml.safe_load(yaml_str)
            if not isinstance(t, dict):
                return False
            if not t.get('id') or not isinstance(t['id'], str):
                return False
            info = t.get('info', {})
            if not info.get('name') or not info.get('severity'):
                return False
            if info['severity'] not in ('info', 'low', 'medium', 'high', 'critical'):
                return False
            if not any(k in t for k in ('http', 'requests', 'network', 'dns', 'tcp')):
                return False
            return True
        except Exception:
            return False

    def _generate_one_template(self, product: str, port, banner: str,
                                os_info: str) -> str | None:
        """Generate and validate a single Nuclei template. One retry on validation failure."""
        user_ctx = {'product': product, 'port': str(port), 'banner': banner, 'os': os_info}

        for attempt in range(2):
            content = self._call(_TEMPLATE_SYSTEM, json.dumps(user_ctx),
                                 max_tokens=700, timeout=45)
            if not content:
                return None

            yaml_str = self._strip_fences(content)
            if self._validate_template(yaml_str):
                log.info(f'Generated template for {product}:{port}')
                return yaml_str

            if attempt == 0:
                log.debug(f'Template invalid for {product}:{port}, retrying with feedback')
                user_ctx['feedback'] = (
                    'Previous attempt was invalid. Ensure: id starts with "ai-gen-", '
                    'info.severity is one of info/low/medium/high/critical, '
                    'and an "http" section with path and matchers is present.'
                )

        log.warning(f'Could not generate valid template for {product}:{port}')
        return None

    def generate_templates(self, scan_details_raw) -> list[str]:
        """
        Generate Nuclei YAML templates from bm12 scan context.
        Returns list of valid YAML strings (max 2). Returns [] on any error.
        Called by nuclei-api before running the scan.
        """
        if not self.enabled:
            return []

        try:
            if isinstance(scan_details_raw, str):
                details = json.loads(scan_details_raw)
            else:
                details = scan_details_raw or {}

            products = details.get('products', [])
            ports    = details.get('ports', [])
            banners  = details.get('banners', {}) if isinstance(details.get('banners'), dict) else {}
            os_info  = details.get('os', '')

            if not products:
                return []

            # Build service list, prefer web ports
            services = []
            for i, product in enumerate(products[:5]):
                port   = ports[i] if i < len(ports) else 'unknown'
                banner = banners.get(str(port), '')
                services.append((product, port, banner))

            services.sort(key=lambda s: 0 if str(s[1]) in ('80', '443', '8080', '8443') else 1)

            templates = []
            for product, port, banner in services[:2]:
                tmpl = self._generate_one_template(product, port, banner, os_info)
                if tmpl:
                    templates.append(tmpl)

            log.info(f'Generated {len(templates)} custom template(s) '
                     f'for {[s[0] for s in services[:2]]}')
            return templates

        except Exception as e:
            log.warning(f'generate_templates failed: {e}')
            return []
