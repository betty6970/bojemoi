from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


class DeploymentType(str, Enum):
    """Types de déploiement supportés"""
    VM = "vm"
    CONTAINER = "container"
    SWARM_SERVICE = "swarm_service"
    COMPOSE_STACK = "compose_stack"


class DeploymentStatus(str, Enum):
    """Statuts de déploiement"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class Environment(str, Enum):
    """Environnements de déploiement"""
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"


class GiteaWebhook(BaseModel):
    """Modèle pour les webhooks Gitea"""
    ref: str
    repository: Dict[str, Any]
    pusher: Dict[str, Any]
    commits: List[Dict[str, Any]]
    head_commit: Optional[Dict[str, Any]] = None


class VMDeploymentConfig(BaseModel):
    """Configuration pour le déploiement d'une VM"""
    name: str = Field(..., description="Nom de la VM")
    template: str = Field(..., description="Template XenServer à utiliser")
    vcpus: int = Field(default=2, ge=1, le=32)
    memory_mb: int = Field(default=2048, ge=512)
    disk_gb: int = Field(default=20, ge=10)
    network: str = Field(default="default")
    environment: Environment
    cloud_init_role: Optional[str] = None
    cloud_init_params: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, str]] = None


class ContainerDeploymentConfig(BaseModel):
    """Configuration pour le déploiement d'un container"""
    name: str = Field(..., description="Nom du container")
    image: str = Field(..., description="Image Docker")
    tag: str = Field(default="latest")
    environment: Environment
    env_vars: Optional[Dict[str, str]] = None
    ports: Optional[List[str]] = None
    volumes: Optional[List[str]] = None
    networks: Optional[List[str]] = None
    restart_policy: str = Field(default="unless-stopped")
    labels: Optional[Dict[str, str]] = None


class SwarmServiceConfig(BaseModel):
    """Configuration pour un service Docker Swarm"""
    name: str
    image: str
    tag: str = "latest"
    replicas: int = Field(default=1, ge=1)
    environment: Environment
    env_vars: Optional[Dict[str, str]] = None
    ports: Optional[List[str]] = None
    networks: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    labels: Optional[Dict[str, str]] = None
    update_config: Optional[Dict[str, Any]] = None


class DeploymentManifest(BaseModel):
    """Manifeste de déploiement global"""
    version: str = "1.0"
    deployment_type: DeploymentType
    environment: Environment
    metadata: Optional[Dict[str, Any]] = None
    vm_config: Optional[VMDeploymentConfig] = None
    container_config: Optional[ContainerDeploymentConfig] = None
    swarm_config: Optional[SwarmServiceConfig] = None


class DeploymentRecord(BaseModel):
    """Enregistrement d'un déploiement dans la base de données"""
    id: Optional[int] = None
    deployment_type: DeploymentType
    name: str
    environment: Environment
    status: DeploymentStatus
    git_commit: str
    git_branch: str
    git_repository: str
    config: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    rollback_from: Optional[int] = None


class HealthCheck(BaseModel):
    """Modèle pour le health check"""
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, bool]
