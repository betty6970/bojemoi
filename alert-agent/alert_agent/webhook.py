import logging

from fastapi import FastAPI, Request, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .config import settings
from .enricher import enrich_alert
from .llm import get_llm_decision
from .actions import validate_action, execute_action
from .alerter import send_telegram_alert
from .db import log_action
from .metrics import alerts_received_total, actions_total

logger = logging.getLogger("alert_agent.webhook")

app = FastAPI(title="alert-agent", docs_url=None, redoc_url=None)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.post("/webhook")
async def webhook(request: Request):
    """Receive Alertmanager webhook payload and process each firing alert."""
    payload = await request.json()
    alerts = payload.get("alerts", [])
    processed = 0

    for alert in alerts:
        status = alert.get("status", "")
        if status != "firing":
            continue

        labels = alert.get("labels", {})
        alert_name = labels.get("alertname", "unknown")
        severity = labels.get("severity", "unknown")

        alerts_received_total.labels(
            alertname=alert_name, severity=severity
        ).inc()

        try:
            await _process_alert(alert, alert_name, severity)
            processed += 1
        except Exception:
            logger.exception("Failed to process alert %s", alert_name)

    return {"processed": processed, "total": len(alerts)}


async def _process_alert(alert: dict, alert_name: str, severity: str):
    """Full pipeline: enrich → LLM → validate → execute → log → notify."""
    # 1. Enrich
    context = await enrich_alert(alert)
    logger.info("Enriched alert %s:\n%s", alert_name, context)

    # 2. LLM decision
    decision = await get_llm_decision(context)

    # 3. Validate
    valid, reason = validate_action(decision)
    if not valid:
        logger.warning(
            "Action rejected for %s: %s (decision=%s)",
            alert_name, reason, decision,
        )
        decision = {
            "action": "noop",
            "reason": f"Rejected: {reason}",
            "params": {},
        }

    action = decision["action"]
    service_name = decision.get("params", {}).get("service_name")

    # 4. Execute
    success, error = await execute_action(decision)

    dry_label = "true" if settings.dry_run else "false"
    success_label = "true" if success else "false"
    actions_total.labels(
        action=action, dry_run=dry_label, success=success_label
    ).inc()

    action_desc = action
    if settings.dry_run and action not in ("noop", "notify_only"):
        action_desc = f"[DRY-RUN] {action}"

    # 5. Log to DB
    await log_action(
        alert_name=alert_name,
        service_name=service_name,
        severity=severity,
        llm_decision=decision,
        action_taken=action_desc,
        dry_run=settings.dry_run,
        success=success,
        error_message=error,
    )

    # 6. Notify Telegram
    await send_telegram_alert(
        alert_name=alert_name,
        service_name=service_name,
        severity=severity,
        decision=decision,
        action_taken=action_desc,
        dry_run=settings.dry_run,
        success=success,
    )

    logger.info(
        "Processed %s → %s (dry_run=%s, success=%s)",
        alert_name, action_desc, settings.dry_run, success,
    )
