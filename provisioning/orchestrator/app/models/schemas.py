"""Pydantic models for request/response validation"""
import re
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, List, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Validation patterns
NAME_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_-]{0,62}$"
NETWORK_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_-]{0,62}$"
TEMPLATE_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_/-]{0,127}$"
IMAGE_PATTERN = r"^[a-z0-9][a-z0-9._/-]*(?::[a-zA-Z0-9._-]+)?(?:@sha256:[a-f0-9]{64})?$"
PORT_PATTERN = r"^\d{1,5}(?::\d{1,5})?(?:/(?:tcp|udp))?$"


class OSType(str, Enum):
    """Supported operating system types"""
    ALPINE = "alpine"
    UBUNTU = "ubuntu"
    DEBIAN = "debian"


class Environment(str, Enum):
    """Deployment environment types"""
    PRODUCTION = "production"
    STAGING = "staging"
    DEV = "dev"


class DeploymentStatus(str, Enum):
    """Deployment status values"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ServiceStatus(str, Enum):
    """Service health status"""
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"


class VMDeployRequest(BaseModel):
    """Request model for VM deployment"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "web-prod-01",
                "template": "webserver",
                "os_type": "alpine",
                "cpu": 4,
                "memory": 4096,
                "disk": 20,
                "network": "default",
                "environment": "production",
                "variables": {"app_port": 8080, "domain": "example.com"},
            }
        }
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=NAME_PATTERN,
        description="VM name (alphanumeric, hyphens, underscores)"
    )
    template: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=TEMPLATE_PATTERN,
        description="Cloud-init template name"
    )
    os_type: OSType = Field(..., description="OS type")
    cpu: int = Field(default=2, ge=1, le=32, description="Number of CPUs")
    memory: int = Field(default=2048, ge=512, le=131072, description="Memory in MB (max 128GB)")
    disk: int = Field(default=20, ge=10, le=2048, description="Disk size in GB (max 2TB)")
    network: str = Field(
        default="default",
        min_length=1,
        max_length=63,
        pattern=NETWORK_PATTERN,
        description="Network name"
    )
    environment: Environment = Field(default=Environment.PRODUCTION, description="Deployment environment")
    variables: Optional[Dict[str, Any]] = Field(default=None, description="Additional cloud-init variables")

    @field_validator("variables")
    @classmethod
    def validate_variables(cls, v):
        """Ensure variables don't contain dangerous keys."""
        if v is None:
            return v
        dangerous_keys = {"__import__", "eval", "exec", "compile", "open", "input"}
        for key in v.keys():
            if key.lower() in dangerous_keys:
                raise ValueError(f"Variable key '{key}' is not allowed")
        return v


class ContainerDeployRequest(BaseModel):
    """Request model for container deployment"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "nginx-proxy",
                "image": "nginx:alpine",
                "replicas": 2,
                "environment": {"NGINX_HOST": "example.com", "NGINX_PORT": "80"},
                "ports": ["80:80", "443:443"],
                "networks": ["backend"],
                "labels": {"traefik.enable": "true"},
            }
        }
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=NAME_PATTERN,
        description="Service name (alphanumeric, hyphens, underscores)"
    )
    image: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Docker image (e.g., nginx:alpine, registry/image:tag)"
    )
    replicas: int = Field(default=1, ge=1, le=100, description="Number of replicas (max 100)")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    ports: List[str] = Field(default_factory=list, description="Port mappings (e.g., '80:80')")
    networks: List[str] = Field(default_factory=lambda: ["backend"], description="Networks to attach")
    labels: Optional[Dict[str, str]] = Field(default=None, description="Service labels")

    @field_validator("image")
    @classmethod
    def validate_image(cls, v):
        """Validate Docker image format."""
        if not re.match(IMAGE_PATTERN, v, re.IGNORECASE):
            raise ValueError(
                f"Invalid image format: {v}. Expected format: registry/image:tag or image:tag"
            )
        return v

    @field_validator("ports")
    @classmethod
    def validate_ports(cls, v):
        """Validate port mappings format."""
        for port in v:
            if not re.match(PORT_PATTERN, port):
                raise ValueError(
                    f"Invalid port format: {port}. Expected format: HOST:CONTAINER or PORT/PROTOCOL"
                )
            # Validate port numbers are in valid range
            parts = re.findall(r"\d+", port)
            for p in parts:
                if int(p) < 1 or int(p) > 65535:
                    raise ValueError(f"Port number {p} out of range (1-65535)")
        return v

    @field_validator("networks")
    @classmethod
    def validate_networks(cls, v):
        """Validate network names."""
        for network in v:
            if not re.match(NETWORK_PATTERN, network):
                raise ValueError(f"Invalid network name: {network}")
        return v


class DeploymentResponse(BaseModel):
    """Response model for deployment operations"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "deployment_id": 123,
                "resource_id": "vm-ref-12345",
                "message": "VM web-prod-01 deployed successfully",
            }
        }
    )

    success: bool
    deployment_id: Optional[int] = None
    resource_id: Optional[str] = None
    message: str


class HealthResponse(BaseModel):
    """Response model for health check"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2025-01-17T10:30:00Z",
                "services": {
                    "gitea": "up",
                    "xenserver": "up",
                    "docker_swarm": "up",
                    "database": "up",
                },
            }
        }
    )

    status: str
    timestamp: datetime
    services: Dict[str, ServiceStatus]


class Deployment(BaseModel):
    """Deployment record"""
    id: int
    type: str
    name: str
    config: Dict[str, Any]
    resource_ref: Optional[str] = None
    status: DeploymentStatus
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DeploymentListResponse(BaseModel):
    """Response model for deployment list"""
    success: bool
    count: int
    deployments: List[Deployment]


# Blockchain models


class BlockchainBlock(BaseModel):
    """Blockchain block record"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "block_number": 1,
                "previous_hash": None,
                "current_hash": "a1b2c3d4e5f6789...",
                "deployment_type": "vm",
                "name": "web-prod-01",
                "config": {"cpu": 4, "memory": 4096},
                "resource_ref": "vm-ref-12345",
                "status": "success",
                "error": None,
                "source_ip": "192.168.1.100",
                "source_country": "FR",
                "created_at": "2025-01-17T10:30:00Z",
            }
        }
    )

    id: int
    block_number: int
    previous_hash: Optional[str] = None
    current_hash: str
    deployment_type: str
    name: str
    config: Dict[str, Any]
    resource_ref: Optional[str] = None
    status: DeploymentStatus
    error: Optional[str] = None
    source_ip: Optional[str] = None
    source_country: Optional[str] = None
    created_at: datetime


class BlockchainVerifyResponse(BaseModel):
    """Response model for blockchain verification"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "valid": True,
                "blocks_checked": 150,
                "message": "Chain integrity verified",
                "error": None,
                "invalid_blocks": None,
            }
        }
    )

    valid: bool
    blocks_checked: int
    message: Optional[str] = None
    error: Optional[str] = None
    invalid_blocks: Optional[List[Dict[str, Any]]] = None


class BlockListResponse(BaseModel):
    """Response model for blockchain blocks list"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "count": 10,
                "blocks": [],
            }
        }
    )

    success: bool
    count: int
    blocks: List[BlockchainBlock]


class BlockchainStatsResponse(BaseModel):
    """Response model for blockchain statistics"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_blocks": 150,
                "deployments_by_type": {"vm": 80, "container": 70},
                "deployments_by_status": {"success": 140, "failed": 10},
                "first_block_time": "2025-01-01T00:00:00Z",
                "last_block_time": "2025-01-17T10:30:00Z",
                "chain_continuous": True,
            }
        }
    )

    total_blocks: int
    deployments_by_type: Dict[str, int]
    deployments_by_status: Dict[str, int]
    first_block_time: Optional[str] = None
    last_block_time: Optional[str] = None
    chain_continuous: bool
    error: Optional[str] = None
