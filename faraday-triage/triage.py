#!/usr/bin/env python3
"""
DefectDojo Triage Agent
Applique des règles déterministes + Mistral (Ollama) sur les findings actifs DefectDojo.

Flow:
  1. GET /api/v2/findings/?active=true&false_positive=false&risk_accepted=false
  2. Règles déterministes → décision immédiate
  3. Cas ambigus → Mistral pour classification
  4. PATCH /api/v2/findings/{id}/ → mise à jour active/risk_accepted/false_p
"""

import os
import json
import time
import logging
import httpx
from prometheus_client import start_http_server, Counter, Gauge
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────────────────────

DOJO_URL     = os.getenv("DEFECTDOJO_URL", "http://defectdojo-nginx:8080").rstrip("/")
DOJO_TOKEN   = ""  # chargé au démarrage depuis /run/secrets/dojo_api_token
OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
DRY_RUN      = os.getenv("DRY_RUN", "true").lower() == "true"
SCHEDULE_HOURS = int(os.getenv("SCHEDULE_HOURS", "6"))
BATCH_SIZE   = int(os.getenv("BATCH_SIZE", "100"))
METRICS_PORT = int(os.getenv("METRICS_PORT", "9303"))
RETRIAGE_DAYS = int(os.getenv("RETRIAGE_DAYS", "7"))


def _load_token() -> str:
    try:
        with open("/run/secrets/dojo_api_token") as f:
            return f.read().strip()
    except FileNotFoundError:
        return os.getenv("DEFECTDOJO_TOKEN", "")


# ─── Prometheus ───────────────────────────────────────────────────────────────

findings_processed     = Counter("triage_findings_processed_total",    "Findings processed",      ["product"])
findings_closed        = Counter("triage_findings_closed_total",       "Findings closed",          ["method"])
findings_risk_accepted = Counter("triage_findings_risk_accepted_total","Findings risk-accepted",   ["method"])
findings_kept_open     = Counter("triage_findings_kept_open_total",    "Findings kept open",       ["method"])
llm_calls              = Counter("triage_llm_calls_total",             "LLM calls",                ["outcome"])
llm_errors             = Counter("triage_llm_errors_total",            "LLM errors")
findings_pending_gauge = Gauge("triage_findings_pending",              "Untriaged active findings", ["severity"])

# ─── Deterministic rules ──────────────────────────────────────────────────────

CLOSE_PREFIXES = ["Honeypot: "]

ALWAYS_RISK_ACCEPT = {
    "User Agent Fuzzer",
    "ZAP is Out of Date",
    "Modern Web Application",
    "Re-examine Cache-control Directives",
    "Timestamp Disclosure - Unix",
    "Sec-Fetch-Dest Header is Missing",
    "Sec-Fetch-Mode Header is Missing",
    "Sec-Fetch-Site Header is Missing",
    "Authentication Request Identified",
    "Information Disclosure - Suspicious Comments",
    "Loosely Scoped Cookie",
}

LOW_SIGNAL_HEADERS = {
    "Content Security Policy (CSP) Header Not Set",
    "X-Content-Type-Options Header Missing",
    "Strict-Transport-Security Header Not Set",
    "Missing Anti-clickjacking Header",
    "X-Frame-Options Header Not Set",
    "Permissions Policy Header Not Set",
    "CSP: style-src unsafe-inline",
    "CSP: script-src unsafe-eval",
    "CSP: script-src unsafe-inline",
    "CSP: Failure to Define Directive with No Fallback",
    "Server Leaks Version Information via \"Server\" HTTP Response Header Field",
    "Cross-Domain JavaScript Source File Inclusion",
}


def apply_rules(finding: dict) -> tuple[str | None, str, str]:
    """
    Returns (decision, reason, method) — or (None, '', '') si LLM nécessaire.
    decision: 'closed' | 'risk-accepted' | None
    """
    title    = finding.get("title", "")
    severity = (finding.get("severity") or "").lower()
    cve_ids  = finding.get("cve_id") or ""
    has_cve  = bool(cve_ids and cve_ids.strip())
    epss     = finding.get("epss_score")

    for prefix in CLOSE_PREFIXES:
        if title.startswith(prefix):
            return "closed", "Honeypot observation — telemetry, not a vuln", "rule"

    if title in ALWAYS_RISK_ACCEPT:
        return "risk-accepted", f"Known scanner noise: {title}", "rule"

    if severity == "informational" and not has_cve:
        return "risk-accepted", "Informational, no CVE", "rule"

    if severity in ("informational", "low") and not has_cve and title in LOW_SIGNAL_HEADERS:
        return "risk-accepted", f"Header hygiene finding, no CVE: {title}", "rule"

    if severity == "low" and not has_cve and (epss is None or epss < 0.01):
        return "risk-accepted", f"Low severity, no CVE, EPSS={epss}", "rule"

    return None, "", ""


# ─── Ollama / Mistral ─────────────────────────────────────────────────────────

PROMPT = """\
Tu es un analyste cybersécurité senior. Analyse ce finding DefectDojo et décide de son statut.

Contexte: environnement lab/homelab de pentest interne, pas de données clients, \
les cibles sont des machines du réseau local ou de l'internet public scannées volontairement.

Réponds UNIQUEMENT avec un JSON valide sur une seule ligne:
{{"decision": "<valeur>", "reason": "<explication courte>"}}

Valeurs possibles:
- "risk-accepted" : faux positif confirmé, bruit de scanner, ou risque négligeable dans ce contexte lab
- "open"          : finding légitime qui mérite investigation ou correction
- "needs-review"  : ambigu, nécessite une review humaine

Finding:
- Titre     : {title}
- Sévérité  : {severity}
- CVE       : {cve}
- EPSS      : {epss}
- Description: {description}

JSON:\
"""


def ask_mistral(finding: dict) -> tuple[str | None, str]:
    prompt = PROMPT.format(
        title       = finding.get("title", ""),
        severity    = finding.get("severity", ""),
        cve         = finding.get("cve_id") or "aucune",
        epss        = finding.get("epss_score") or "N/A",
        description = (finding.get("description") or "")[:600],
    )

    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model":   OLLAMA_MODEL,
                "prompt":  prompt,
                "stream":  False,
                "format":  "json",
                "options": {"temperature": 0.1, "num_predict": 150},
            },
            timeout=90,
        )
        resp.raise_for_status()
        raw    = resp.json().get("response", "")
        parsed = json.loads(raw)
        decision = str(parsed.get("decision", "")).strip()
        reason   = str(parsed.get("reason", "")).strip()[:300]

        if decision not in ("risk-accepted", "open", "needs-review"):
            log.warning("Unexpected LLM decision %r for finding#%s", decision, finding.get("id"))
            llm_errors.inc()
            return None, ""

        return decision, reason

    except Exception as exc:
        log.error("Ollama error finding#%s: %s", finding.get("id"), exc)
        llm_errors.inc()
        return None, ""


# ─── DefectDojo API ───────────────────────────────────────────────────────────

def _headers() -> dict:
    return {"Authorization": f"Token {DOJO_TOKEN}"} if DOJO_TOKEN else {}


def fetch_batch(offset: int = 0) -> tuple[list[dict], int]:
    """Retourne (findings, total_count) — findings actifs non triés."""
    try:
        r = httpx.get(
            f"{DOJO_URL}/api/v2/findings/",
            headers=_headers(),
            params={
                "active":         "true",
                "false_positive": "false",
                "risk_accepted":  "false",
                "limit":          BATCH_SIZE,
                "offset":         offset,
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("results", []), data.get("count", 0)
    except Exception as exc:
        log.error("Failed to fetch findings from DefectDojo: %s", exc)
        return [], 0


def get_severity_counts() -> dict:
    """Retourne le nombre de findings actifs par sévérité."""
    counts = {}
    for severity in ("Critical", "High", "Medium", "Low", "Info"):
        try:
            r = httpx.get(
                f"{DOJO_URL}/api/v2/findings/",
                headers=_headers(),
                params={"active": "true", "false_positive": "false",
                        "risk_accepted": "false", "severity": severity, "limit": 1},
                timeout=15,
            )
            r.raise_for_status()
            counts[severity.lower()] = r.json().get("count", 0)
        except Exception:
            counts[severity.lower()] = 0
    return counts


def apply_decision(finding_id: int, decision: str, reason: str):
    """Applique la décision sur DefectDojo via PATCH."""
    if DRY_RUN:
        return

    if decision == "closed":
        patch = {"active": False, "false_p": True, "risk_accepted": False}
    elif decision == "risk-accepted":
        patch = {"active": False, "risk_accepted": True, "false_p": False}
    else:
        return  # 'open' / 'needs-review' → on ne touche pas

    try:
        r = httpx.patch(
            f"{DOJO_URL}/api/v2/findings/{finding_id}/",
            headers=_headers(),
            json=patch,
            timeout=15,
        )
        r.raise_for_status()
    except Exception as exc:
        log.error("Failed to patch finding#%d: %s", finding_id, exc)


# ─── Triage run ───────────────────────────────────────────────────────────────

def run_triage():
    log.info("=== Triage run start (dry_run=%s, url=%s) ===", DRY_RUN, DOJO_URL)

    counts = get_severity_counts()
    total = sum(counts.values())
    for sev, cnt in counts.items():
        findings_pending_gauge.labels(severity=sev).set(cnt)
    log.info("Pending: %d findings — %s", total, counts)

    if total == 0:
        log.info("Nothing to triage.")
        return

    stats = {"closed": 0, "risk-accepted": 0, "open": 0, "needs-review": 0, "skipped": 0}
    offset = 0

    while True:
        batch, total_count = fetch_batch(offset)
        if not batch:
            break

        for finding in batch:
            fid = finding.get("id")
            product_name = (finding.get("test_object") or {}).get("engagement_name", "unknown")
            findings_processed.labels(product=product_name).inc()

            decision, reason, method = apply_rules(finding)

            if decision is None:
                decision, reason = ask_mistral(finding)
                method = "llm"
                if decision is None:
                    stats["skipped"] += 1
                    continue
                llm_calls.labels(outcome=decision).inc()

            prefix = "[DRY RUN] " if DRY_RUN else ""
            log.info(
                "%sfinding#%s [%s] '%s' → %s (%s): %s",
                prefix, fid, finding.get("severity"), finding.get("title"),
                decision, method, reason,
            )

            apply_decision(fid, decision, reason)
            stats[decision] = stats.get(decision, 0) + 1

            if decision == "closed":
                findings_closed.labels(method=method).inc()
            elif decision == "risk-accepted":
                findings_risk_accepted.labels(method=method).inc()
            else:
                findings_kept_open.labels(method=method).inc()

            if method == "llm":
                time.sleep(2)

        offset += len(batch)
        if offset >= total_count:
            break

    log.info(
        "=== Triage done: closed=%d risk_accepted=%d open=%d needs_review=%d skipped=%d ===",
        stats["closed"], stats["risk-accepted"], stats["open"],
        stats.get("needs-review", 0), stats["skipped"],
    )


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    DOJO_TOKEN = _load_token()
    if not DOJO_TOKEN:
        log.warning("No DefectDojo API token found — set dojo_api_token secret or DEFECTDOJO_TOKEN env var")

    log.info("DefectDojo Triage Agent | model=%s | dry_run=%s | every %dh | url=%s",
             OLLAMA_MODEL, DRY_RUN, SCHEDULE_HOURS, DOJO_URL)

    start_http_server(METRICS_PORT)
    log.info("Prometheus metrics on :%d", METRICS_PORT)

    try:
        run_triage()
    except Exception as exc:
        log.error("Initial run failed: %s", exc, exc_info=True)

    sched = BlockingScheduler(timezone="UTC")
    sched.add_job(run_triage, "interval", hours=SCHEDULE_HOURS, misfire_grace_time=600)
    log.info("Scheduler started — next run in %dh", SCHEDULE_HOURS)
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down.")
