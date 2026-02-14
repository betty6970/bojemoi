from prometheus_client import Counter, Gauge

feeds_total = Counter(
    "dozor_feeds_total",
    "Feed download attempts",
    ["feed", "status"],
)

ips_total = Gauge(
    "dozor_ips_total",
    "Total unique IPs/CIDRs in blocklist",
)

ips_by_feed = Gauge(
    "dozor_ips_by_feed",
    "IPs/CIDRs per feed",
    ["feed"],
)

last_update_timestamp = Gauge(
    "dozor_last_update_timestamp",
    "Unix timestamp of last successful update",
)

reload_total = Counter(
    "dozor_reload_total",
    "Suricata reload attempts",
    ["status"],
)
