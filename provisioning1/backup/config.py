import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuration de l'orchestrateur de déploiement"""
    
    # API Configuration
    app_name: str = "Deployment Orchestrator"
    app_version: str = "1.0.0"
    webhook_port: int = int(os.getenv("WEBHOOK_PORT", "8080"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Gitea Configuration
    gitea_url: str = os.getenv("GITEA_URL", "https://gitea.bojemoi.me")
    gitea_token: Optional[str] = os.getenv("GITEA_TOKEN")
    gitea_webhook_secret: Optional[str] = os.getenv("GITEA_WEBHOOK_SECRET")
    
    # PostgreSQL Configuration
    postgres_host: str = os.getenv("POSTGRES_HOST", "postgres.bojemoi.lab")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "deployments")
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "bojemoi")
    
    # XenServer Configuration
    xenserver_url: str = os.getenv("XENSERVER_URL", "https://xenserver.bojemoi.lab")
    xenserver_user: str = os.getenv("XENSERVER_USER", "root")
    xenserver_password: str = os.getenv("XENSERVER_PASSWORD", "Sysres@01")
    
    # Docker Configuration
    docker_host: Optional[str] = os.getenv("DOCKER_HOST")  # None = local socket
    docker_swarm_enabled: bool = os.getenv("DOCKER_SWARM_ENABLED", "true").lower() == "true"
    
    # Cloud-init Configuration
    cloud_init_datasource_url: str = os.getenv("CLOUD_INIT_DATASOURCE_URL", "http://bojemoi.bojemoi.lab")
    
    # Prometheus Configuration
    prometheus_enabled: bool = os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true"
    prometheus_port: int = int(os.getenv("PROMETHEUS_PORT", "9090"))
    
    # Cache Configuration
    cache_dir: str = "/app/cache"
    templates_dir: str = "/app/templates"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
