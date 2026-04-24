"""Application configuration with secure defaults.

All sensitive values are read from Docker secrets (/run/secrets/).
Fallback to environment variables for local development only.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Optional
from pathlib import Path
import os

SECRETS_DIR = Path("/run/secrets")


def _read_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """Read a Docker secret from /run/secrets/, fallback to env var."""
    secret_file = SECRETS_DIR / name
    if secret_file.is_file():
        return secret_file.read_text().strip()
    return os.getenv(name.upper(), default)


class Settings(BaseSettings):
    """Application settings with secure defaults.

    SECURITY: All credentials are read from Docker secrets.
    Fallback to env vars for local dev only.
    """

    # App
    APP_NAME: str = "Bojemoi Orchestrator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 1
    API_TITLE: str = "Bojemoi API Orchestrator"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "VM and Container Deployment Orchestration"

    # Database
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = Field(
        default_factory=lambda: _read_secret("postgres_password") or "",
        description="Database password (from Docker secret)"
    )
    POSTGRES_DB: str = "msf"

    # IP2Location Database
    IP2LOCATION_DB_NAME: str = "ip2location"

    # Karacho Blockchain Database
    KARACHO_DB_NAME: str = "karacho"

    # Metasploit Database (host_debug pour debug uzi)
    MSF_DB_NAME: str = "msf"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def IP2LOCATION_DB_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.IP2LOCATION_DB_NAME}"

    @property
    def KARACHO_DB_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.KARACHO_DB_NAME}"

    @property
    def MSF_DB_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.MSF_DB_NAME}"

    # IP Validation
    IP_VALIDATION_ENABLED: bool = True
    ALLOWED_COUNTRIES: List[str] = Field(
        default_factory=lambda: ["FR", "DE", "CH", "BE", "LU", "NL", "AT"],
        description="Allowed countries for IP validation"
    )

    # Gitea
    GITEA_URL: str = "https://gitea.bojemoi.me"
    GITEA_TOKEN: str = Field(
        default_factory=lambda: _read_secret("gitea_token") or "",
        description="Gitea API token (from Docker secret)"
    )
    GITEA_REPO_OWNER: str = "bojemoi"
    GITEA_REPO: str = "bojemoi-configs"

    # XenServer
    XENSERVER_URL: str = "https://xenserver.bojemoi.lab"
    XENSERVER_HOST: str = "xenserver.bojemoi.lab"
    XENSERVER_USER: str = "root"
    XENSERVER_PASS: str = Field(
        default_factory=lambda: _read_secret("xenserver_pass") or "",
        description="XenServer password (from Docker secret)"
    )
    # UUID of the Alpine root VDI used as boot disk source when the template has no disk.
    # Find with: session.xenapi.VDI.get_all() filtered by name_label='alpine root'
    ALPINE_BOOT_VDI_UUID: str = "df288d22-9c34-410f-8392-6af76151f14a"

    # Docker
    DOCKER_HOST: str = "unix:///var/run/docker.sock"
    DOCKER_SWARM_MANAGER: bool = True
    DOCKER_SWARM_URL: str = "unix:///var/run/docker.sock"

    # Scheduler
    CHECK_INTERVAL_MINUTES: int = 5
    ENABLE_SCHEDULER: bool = True

    # Templates (local bind-mount — no Gitea dependency at runtime)
    TEMPLATES_DIR: str = "/app/cloud-init"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "/app/logs"

    # CORS - Restrict origins in production
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: ["https://bojemoi.me", "https://admin.bojemoi.me"],
        description="Allowed CORS origins"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("POSTGRES_PASSWORD", "GITEA_TOKEN", "XENSERVER_PASS", mode="before")
    @classmethod
    def validate_secrets(cls, v, info):
        """Ensure secrets are not default/placeholder values."""
        if v in (None, "", "changeme", "password", "secret"):
            raise ValueError(
                f"{info.field_name} must be set — provide via Docker secret "
                f"(/run/secrets/{info.field_name.lower()}) or env var"
            )
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()

