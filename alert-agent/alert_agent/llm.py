import json
import logging
import time

import httpx

from .config import settings
from .metrics import llm_requests_total, llm_duration_seconds

logger = logging.getLogger("alert_agent.llm")

SYSTEM_PROMPT = """\
You are a Docker Swarm operations assistant. You receive Prometheus alerts \
with Docker context and must decide on ONE remediation action.

Available actions:
- restart_service: Force-restart a service (params: service_name)
- scale_up: Increase replicas (params: service_name, replicas)
- scale_down: Decrease replicas (params: service_name, replicas)
- noop: No action needed
- notify_only: Just send a notification (params: message)

Rules:
- NEVER touch critical services: base_postgres, base_prometheus, base_alertmanager
- Scale up max 10 replicas, scale down min 1
- Prefer restart_service for crash loops or OOM
- Prefer scale_up for high load / resource pressure
- Prefer noop for informational or low-severity alerts
- Prefer notify_only when human intervention is needed

Respond with ONLY a JSON object:
{"action": "<action>", "reason": "<brief reason>", "params": {<params>}}
"""


async def get_llm_decision(enriched_context: str) -> dict:
    """Call Ollama for a remediation decision. Returns parsed JSON or noop fallback."""
    url = f"{settings.ollama_base_url}/api/chat"
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": enriched_context},
        ],
        "stream": False,
        "format": "json",
    }

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()

        elapsed = time.monotonic() - start
        llm_duration_seconds.observe(elapsed)

        body = resp.json()
        content = body.get("message", {}).get("content", "")
        decision = json.loads(content)

        # Validate required fields
        if "action" not in decision:
            raise ValueError("Missing 'action' field")

        decision.setdefault("reason", "")
        decision.setdefault("params", {})
        llm_requests_total.labels(status="success").inc()
        logger.info("LLM decision: %s (%.1fs)", decision["action"], elapsed)
        return decision

    except Exception as exc:
        elapsed = time.monotonic() - start
        llm_duration_seconds.observe(elapsed)
        llm_requests_total.labels(status="error").inc()
        logger.exception("LLM call failed, falling back to noop")

        # One retry
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            body = resp.json()
            content = body.get("message", {}).get("content", "")
            decision = json.loads(content)
            if "action" not in decision:
                raise ValueError("Missing 'action' field")
            decision.setdefault("reason", "")
            decision.setdefault("params", {})
            llm_requests_total.labels(status="success").inc()
            return decision
        except Exception:
            logger.warning("LLM retry also failed")

        return {
            "action": "noop",
            "reason": f"LLM unavailable: {exc}",
            "params": {},
        }
