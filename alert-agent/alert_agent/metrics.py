from prometheus_client import Counter, Histogram

alerts_received_total = Counter(
    "alert_agent_alerts_received_total",
    "Alerts received from Alertmanager",
    ["alertname", "severity"],
)

actions_total = Counter(
    "alert_agent_actions_total",
    "Actions taken (or dry-run logged)",
    ["action", "dry_run", "success"],
)

llm_requests_total = Counter(
    "alert_agent_llm_requests_total",
    "LLM inference requests",
    ["status"],
)

llm_duration_seconds = Histogram(
    "alert_agent_llm_duration_seconds",
    "LLM inference duration",
    buckets=[0.5, 1, 2, 5, 10, 15, 20, 30, 60],
)
