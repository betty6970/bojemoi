from pathlib import Path
from pydantic_settings import BaseSettings


def _read_secret(name: str, default: str = "") -> str:
    """Read a Docker secret file, return default if not found."""
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
    pg_database: str = "razvedka"

    # Telegram API (loaded from secrets in main.py, defaults here for dev)
    telegram_api_id: int = 0
    telegram_api_hash: str = ""
    telegram_phone: str = ""

    # Channels to monitor (comma-separated)
    telegram_channels: str = (
        "ddos_separ,"
        "RVvoenkor,"
        "CyberArmyofRussia,"
        "killnet_info,"
        "XakNet_Team,"
        "SolntsepekZ,"
        "russian_hackers_team"
    )

    # Scoring thresholds
    buzz_check_interval: int = 60  # minutes
    alert_channel_threshold: int = 3  # min distinct channels for alert
    alert_mention_threshold: int = 5  # min mentions for alert

    # Alert destinations
    telegram_bot_token: str = ""
    telegram_alert_chat_id: str = ""
    alertmanager_webhook_url: str = "http://alertmanager:9093/api/v1/alerts"
    custom_webhook_url: str = ""

    # Metrics
    metrics_port: int = 9300

    model_config = {"env_prefix": ""}

    def load_secrets(self):
        """Override settings with Docker secrets if available."""
        api_id = _read_secret("telegram_api_id")
        if api_id:
            self.telegram_api_id = int(api_id)
        api_hash = _read_secret("telegram_api_hash")
        if api_hash:
            self.telegram_api_hash = api_hash
        phone = _read_secret("telegram_phone")
        if phone:
            self.telegram_phone = phone
        bot_token = _read_secret("telegram_bot_token")
        if bot_token:
            self.telegram_bot_token = bot_token
        chat_id = _read_secret("telegram_alert_chat_id")
        if chat_id:
            self.telegram_alert_chat_id = chat_id


settings = Settings()
