from prometheus_client import Counter, Gauge

polls_total = Counter(
    "vigie_polls_total", "Number of RSS feed polls", ["feed"]
)
items_total = Counter(
    "vigie_items_total", "New items discovered", ["feed", "category"]
)
matches_total = Counter(
    "vigie_matches_total", "Items matched by watchlist", ["category"]
)
alerts_sent_total = Counter(
    "vigie_alerts_sent_total", "Alerts sent", ["channel", "status"]
)
last_poll_timestamp = Gauge(
    "vigie_last_poll_timestamp", "Timestamp of last poll", ["feed"]
)
