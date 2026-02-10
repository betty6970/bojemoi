from prometheus_client import Counter, Histogram, start_http_server

from .config import settings

connections_total = Counter(
    "medved_connections_total",
    "Total honeypot connections",
    ["protocol"],
)

auth_attempts_total = Counter(
    "medved_auth_attempts_total",
    "Total authentication attempts",
    ["protocol"],
)

events_total = Counter(
    "medved_events_total",
    "Total honeypot events",
    ["protocol", "event_type"],
)

faraday_reports_total = Counter(
    "medved_faraday_reports_total",
    "Events reported to Faraday",
    ["status"],
)

connection_duration = Histogram(
    "medved_connection_duration_seconds",
    "Connection duration in seconds",
    ["protocol"],
)


def start_metrics_server():
    start_http_server(settings.metrics_port)
