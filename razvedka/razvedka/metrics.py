from prometheus_client import Counter, Gauge, Histogram

messages_received_total = Counter(
    "razvedka_messages_received_total",
    "Total messages received from Telegram",
    ["channel"],
)

messages_processed_total = Counter(
    "razvedka_messages_processed_total",
    "Total messages processed with extraction",
    ["channel", "language"],
)

entities_extracted_total = Counter(
    "razvedka_entities_extracted_total",
    "Total entities extracted from messages",
    ["entity_type"],
)

france_mentions_total = Counter(
    "razvedka_france_mentions_total",
    "Messages mentioning France-related targets",
    ["channel"],
)

intention_score_histogram = Histogram(
    "razvedka_intention_score",
    "Distribution of intention scores",
    buckets=[0, 1, 2, 3, 5, 8, 10, 15, 20, 50],
)

france_score_histogram = Histogram(
    "razvedka_france_score",
    "Distribution of France relevance scores",
    buckets=[0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 1.0],
)

buzz_clusters_detected_total = Counter(
    "razvedka_buzz_clusters_detected_total",
    "Buzz clusters detected by scorer",
)

alerts_sent_total = Counter(
    "razvedka_alerts_sent_total",
    "Alerts sent to notification channels",
    ["channel_type", "status"],
)

active_channels = Gauge(
    "razvedka_active_channels",
    "Number of actively monitored Telegram channels",
)
