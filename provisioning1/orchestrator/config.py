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
    GITEA_TOKEN: str = ""
    GITEA_REPO_OWNER: str = "bojemoi"
    GITEA_REPO_NAME: str = "infrastructure"
    
    # XenServer
    XENSERVER_HOST: str = "xenserver.bojemoi.lab"
    XENSERVER_USER: str = "root"
    XENSERVER_PASSWORD: str = "Sysres@01"
    
    # Docker
    DOCKER_HOST: str = "unix:///var/run/docker.sock"
    DOCKER_SWARM_MANAGER: bool = True
    
    # Scheduler
    CHECK_INTERVAL_MINUTES: int = 5
    ENABLE_SCHEDULER: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "/app/logs"
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

