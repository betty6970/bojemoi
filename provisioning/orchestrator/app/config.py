from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
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
    POSTGRES_PASSWORD: str = "bojemoi"
    POSTGRES_DB: str = "deployments"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Gitea
    GITEA_URL: str = "https://gitea.bojemoi.me"
    GITEA_TOKEN: str = "8c00a569574268e763f0cfd332104ba98ffb36e5"
    GITEA_REPO_OWNER: str = "bojemoi"
    GITEA_REPO: str = "bojemoi-configs"
    
    # XenServer
    XENSERVER_URL: str = "https://xenserver.bojemoi.lab"
    XENSERVER_HOST: str = "xenserver.bojemoi.lab"
    XENSERVER_USER: str = "root"
    XENSERVER_PASS: str = "Sysres@01"
    
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
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    class Config:
        env_file = "/app/app/.env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()

