"""Application configuration with secure defaults.

All sensitive values MUST be provided via environment variables.
No secrets are stored in code.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Optional
import os


def _require_env(var_name: str, default: Optional[str] = None) -> str:
    """Require environment variable or raise error in production."""
    value = os.getenv(var_name, default)
    if value is None:
        raise ValueError(f"Required environment variable {var_name} is not set")
    return value


class Settings(BaseSettings):
    """Application settings with secure defaults.

    SECURITY: All credentials must be provided via environment variables.
    Default values are only used for non-sensitive configuration.
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

    # Database - NO DEFAULT PASSWORD
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = Field(..., description="Database password (required)")
    POSTGRES_DB: str = "deployments"

    # IP2Location Database
    IP2LOCATION_DB_NAME: str = "ip2location"

    # Karacho Blockchain Database
    KARACHO_DB_NAME: str = "karacho"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def IP2LOCATION_DB_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.IP2LOCATION_DB_NAME}"

    @property
    def KARACHO_DB_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.KARACHO_DB_NAME}"

    # IP Validation
    IP_VALIDATION_ENABLED: bool = True
    ALLOWED_COUNTRIES: List[str] = Field(
        default_factory=lambda: ["FR", "DE", "CH", "BE", "LU", "NL", "AT"],
        description="Allowed countries for IP validation"
    )

    # Gitea - NO DEFAULT TOKEN
    GITEA_URL: str = "https://gitea.bojemoi.me"
    GITEA_TOKEN: str = Field(..., description="Gitea API token (required)")
    GITEA_REPO_OWNER: str = "bojemoi"
    GITEA_REPO: str = "bojemoi-configs"

    # XenServer - NO DEFAULT PASSWORD
    XENSERVER_URL: str = "https://xenserver.bojemoi.lab"
    XENSERVER_HOST: str = "xenserver.bojemoi.lab"
    XENSERVER_USER: str = "root"
    XENSERVER_PASS: str = Field(..., description="XenServer password (required)")

    # Docker
    DOCKER_HOST: str = "unix:///var/run/docker.sock"
    DOCKER_SWARM_MANAGER: bool = True
    DOCKER_SWARM_URL: str = "unix:///var/run/docker.sock"

    # Scheduler
    CHECK_INTERVAL_MINUTES: int = 5
    ENABLE_SCHEDULER: bool = True

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
            raise ValueError(f"{info.field_name} must be set to a secure value")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()

