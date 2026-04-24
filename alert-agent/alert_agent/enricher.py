import logging

import httpx

from .config import settings

logger = logging.getLogger("alert_agent.enricher")


async def enrich_alert(alert: dict) -> str:
    """Enrich an alert with Docker service context.

    Returns a structured text block for the LLM prompt.
    """
    labels = alert.get("labels", {})
    service_name = (
        labels.get("container_label_com_docker_swarm_service_name")
        or labels.get("service")
        or labels.get("job")
        or ""
    )

    parts = [
        f"Alert: {labels.get('alertname', 'unknown')}",
        f"Severity: {labels.get('severity', 'unknown')}",
        f"Service: {service_name or 'N/A'}",
        f"Instance: {labels.get('instance', 'N/A')}",
    ]

    annotations = alert.get("annotations", {})
    if annotations.get("summary"):
        parts.append(f"Summary: {annotations['summary']}")
    if annotations.get("description"):
        parts.append(f"Description: {annotations['description']}")

    # Enrich with Docker API if we have a service name
    if service_name:
        docker_ctx = await _get_docker_context(service_name)
        if docker_ctx:
            parts.append("")
            parts.append("Docker context:")
            parts.append(docker_ctx)

    return "\n".join(parts)


async def _get_docker_context(service_name: str) -> str | None:
    """Fetch service info + task states from Docker socket proxy."""
    base = settings.docker_socket_proxy_url.rstrip("/")
    lines = []

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Service inspect
            resp = await client.get(f"{base}/services/{service_name}")
            if resp.status_code == 200:
                svc = resp.json()
                spec = svc.get("Spec", {})
                mode = spec.get("Mode", {})
                if "Replicated" in mode:
                    replicas = mode["Replicated"].get("Replicas", "?")
                    lines.append(f"  Replicas configured: {replicas}")
                update_status = svc.get("UpdateStatus", {})
                if update_status.get("State"):
                    lines.append(f"  Update state: {update_status['State']}")

            # Task list for this service
            import json as _json
            filters = _json.dumps({"service": [service_name]})
            resp = await client.get(f"{base}/tasks", params={"filters": filters})
            if resp.status_code == 200:
                tasks = resp.json()
                state_counts: dict[str, int] = {}
                for t in tasks:
                    state = t.get("Status", {}).get("State", "unknown")
                    state_counts[state] = state_counts.get(state, 0) + 1
                if state_counts:
                    lines.append(f"  Task states: {state_counts}")

                # Count recent restarts (tasks in 'failed' or 'rejected')
                failed = sum(
                    v for k, v in state_counts.items()
                    if k in ("failed", "rejected", "shutdown")
                )
                if failed:
                    lines.append(f"  Failed/rejected tasks: {failed}")

            # Last 30 lines of logs
            svc_id = svc.get("ID", service_name) if resp.status_code == 200 else service_name
            resp = await client.get(
                f"{base}/services/{svc_id}/logs",
                params={"tail": "30", "stdout": "true", "stderr": "true"},
            )
            if resp.status_code == 200 and resp.text.strip():
                log_text = resp.text.strip()
                # Truncate to avoid huge prompts
                if len(log_text) > 2000:
                    log_text = log_text[:2000] + "\n  ... (truncated)"
                lines.append(f"  Recent logs:\n{log_text}")

    except Exception:
        logger.exception("Failed to enrich from Docker API for %s", service_name)
        return None

    return "\n".join(lines) if lines else None
