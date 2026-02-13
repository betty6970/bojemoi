import logging

from vigie.config import settings

logger = logging.getLogger(__name__)


def match_products(item: dict) -> list[str]:
    """Return watchlist products found in the bulletin title+summary."""
    text = (item.get("title", "") + " " + item.get("summary", "")).lower()
    watchlist = settings.get_watchlist()
    return [product for product in watchlist if product in text]


def should_alert(item: dict, matched: list[str]) -> bool:
    """Decide whether to send an alert for this bulletin."""
    # Alertes CERT-FR are rare and critical — always alert
    if item["category"] == "alerte":
        return True
    # Avis/IOC — alert only if a watched product matches
    return len(matched) > 0
