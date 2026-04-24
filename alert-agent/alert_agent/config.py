from pathlib import Path
from pydantic_settings import BaseSettings


def _read_secret(name: str, default: str = "") -> str:
    path = Path(f"/run/secrets/{name}")
    if path.exists():
        return path.read_text().strip()
    return default


class Settings(BaseSettings):
    # Ollama / LLM
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "mistral"

    # Dry-run mode (default: True — log actions without executing)
    dry_run: bool = True

    # PostgreSQL
    pg_host: str = "postgres"
    pg_port: int = 5432
    pg_user: str = "postgres"
    pg_password: str = "bojemoi"
    pg_database: str = "alert_agent"

    # Docker socket proxy
    docker_socket_proxy_url: str = "http://docker-socket-proxy:2375"

    # Telegram alerting
    telegram_bot_token: str = ""
    telegram_alert_chat_id: str = ""

    # Metrics
    metrics_port: int = 9302

    # Cooldown between actions on same service (seconds)
    cooldown_seconds: int = 300

    # Max replicas when scaling up
    max_replicas: int = 10

    model_config = {"env_prefix": ""}

    def load_secrets(self):
        pg_pass = _read_secret("postgres_password")
        if pg_pass:
            self.pg_password = pg_pass
        token = _read_secret("telegram_bot_token")
        if token:
            self.telegram_bot_token = token
        chat_id = _read_secret("telegram_alert_chat_id")
        if chat_id:
            self.telegram_alert_chat_id = chat_id


settings = Settings()
settings.load_secrets()
