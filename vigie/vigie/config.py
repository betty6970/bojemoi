from pathlib import Path
from pydantic_settings import BaseSettings


def _read_secret(name: str, default: str = "") -> str:
    path = Path(f"/run/secrets/{name}")
    if path.exists():
        return path.read_text().strip()
    return default


class Settings(BaseSettings):
    # PostgreSQL
    pg_host: str = "postgres"
    pg_port: int = 5432
    pg_user: str = "postgres"
    pg_password: str = "bojemoi"
    pg_database: str = "vigie"

    # CERT-FR feeds
    feed_urls: str = (
        "https://cert.ssi.gouv.fr/alerte/feed/,"
        "https://cert.ssi.gouv.fr/avis/feed/,"
        "https://cert.ssi.gouv.fr/ioc/feed/"
    )
    poll_interval: int = 300

    # Product watchlist (comma-separated, case-insensitive match on title+summary)
    watchlist: str = (
        "linux,docker,postgresql,postgres,traefik,grafana,prometheus,"
        "suricata,nginx,python,alpine,openssl,openssh,git,curl,"
        "ruby,node,fastapi,redis,loki"
    )

    # Alerting
    telegram_bot_token: str = ""
    telegram_alert_chat_id: str = ""
    alertmanager_webhook_url: str = "http://alertmanager:9093/api/v1/alerts"

    # Metrics
    metrics_port: int = 9301

    def load_secrets(self):
        token = _read_secret("telegram_bot_token")
        if token:
            self.telegram_bot_token = token
        chat_id = _read_secret("telegram_alert_chat_id")
        if chat_id:
            self.telegram_alert_chat_id = chat_id

    def get_feed_urls(self) -> list[str]:
        return [u.strip() for u in self.feed_urls.split(",") if u.strip()]

    def get_watchlist(self) -> list[str]:
        return [w.strip().lower() for w in self.watchlist.split(",") if w.strip()]


settings = Settings()
