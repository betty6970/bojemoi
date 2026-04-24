import logging
import time

import httpx

from .config import settings

logger = logging.getLogger("alert_agent.actions")

VALID_ACTIONS = {"restart_service", "scale_up", "scale_down", "noop", "notify_only"}

# Services that must never be touched
SERVICE_BLACKLIST = {
    "base_postgres",
    "base_prometheus",
    "base_alertmanager",
    "base_grafana",
    "base_loki",
}

# Track last action time per service for cooldown
_last_action: dict[str, float] = {}


def validate_action(decision: dict) -> tuple[bool, str]:
    """Validate LLM decision against whitelist and guardrails.

    Returns (valid, reason).
    """
    action = decision.get("action", "")
    params = decision.get("params", {})

    if action not in VALID_ACTIONS:
        return False, f"Unknown action: {action}"

    if action in ("noop", "notify_only"):
        return True, ""

    service_name = params.get("service_name", "")
    if not service_name:
        return False, "Missing service_name param"

    if service_name in SERVICE_BLACKLIST:
        return False, f"Service {service_name} is blacklisted"

    # Cooldown check
    last = _last_action.get(service_name, 0)
    elapsed = time.time() - last
    if elapsed < settings.cooldown_seconds:
        remaining = int(settings.cooldown_seconds - elapsed)
        return False, f"Cooldown active for {service_name} ({remaining}s remaining)"

    if action == "scale_up":
        replicas = params.get("replicas", 0)
        if not isinstance(replicas, int) or replicas < 1:
            return False, "Invalid replicas for scale_up"
        if replicas > settings.max_replicas:
            return False, f"Replicas {replicas} exceeds max {settings.max_replicas}"

    if action == "scale_down":
        replicas = params.get("replicas", 0)
        if not isinstance(replicas, int) or replicas < 1:
            return False, "Cannot scale below 1 replica"

    return True, ""


async def execute_action(decision: dict) -> tuple[bool, str | None]:
    """Execute a validated action. Returns (success, error_message)."""
    action = decision["action"]
    params = decision.get("params", {})

    if action in ("noop", "notify_only"):
        return True, None

    service_name = params["service_name"]

    if settings.dry_run:
        logger.info("[DRY-RUN] Would execute %s on %s (params=%s)", action, service_name, params)
        _last_action[service_name] = time.time()
        return True, None

    base = settings.docker_socket_proxy_url.rstrip("/")

    try:
        if action == "restart_service":
            async with httpx.AsyncClient(timeout=30) as client:
                # Fetch current spec + version
                svc_resp = await client.get(f"{base}/services/{service_name}")
                if svc_resp.status_code != 200:
                    return False, f"Service not found: {service_name}"
                svc = svc_resp.json()
                version = svc.get("Version", {}).get("Index", 0)
                spec = svc.get("Spec", {})
                spec["TaskTemplate"] = spec.get("TaskTemplate", {})
                spec["TaskTemplate"]["ForceUpdate"] = (
                    spec["TaskTemplate"].get("ForceUpdate", 0) + 1
                )
                resp = await client.post(
                    f"{base}/services/{service_name}/update",
                    params={"version": str(version)},
                    json=spec,
                )
                resp.raise_for_status()

        elif action == "scale_up":
            replicas = params["replicas"]
            success, err = await _scale_service(base, service_name, replicas)
            if not success:
                return False, err

        elif action == "scale_down":
            replicas = params["replicas"]
            success, err = await _scale_service(base, service_name, replicas)
            if not success:
                return False, err

        _last_action[service_name] = time.time()
        logger.info("Executed %s on %s", action, service_name)
        return True, None

    except Exception as exc:
        logger.exception("Failed to execute %s on %s", action, service_name)
        return False, str(exc)


async def _scale_service(base: str, service_name: str, replicas: int) -> tuple[bool, str | None]:
    """Scale a service to the given replica count."""
    async with httpx.AsyncClient(timeout=30) as client:
        svc_resp = await client.get(f"{base}/services/{service_name}")
        if svc_resp.status_code != 200:
            return False, f"Service not found: {service_name}"
        svc = svc_resp.json()
        version = svc.get("Version", {}).get("Index", 0)
        spec = svc.get("Spec", {})
        mode = spec.get("Mode", {})
        if "Replicated" not in mode:
            return False, "Service is not replicated"
        mode["Replicated"]["Replicas"] = replicas
        resp = await client.post(
            f"{base}/services/{service_name}/update",
            params={"version": str(version)},
            json=spec,
        )
        resp.raise_for_status()
    return True, None
