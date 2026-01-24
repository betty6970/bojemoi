"""Pydantic models for request/response validation"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime


class VMDeployRequest(BaseModel):
    """Request model for VM deployment"""
    name: str = Field(..., description="VM name")
    template: str = Field(..., description="Cloud-init template name")
    os_type: str = Field(..., description="OS type: alpine, ubuntu, debian")
    cpu: int = Field(default=2, ge=1, le=32, description="Number of CPUs")
    memory: int = Field(default=2048, ge=512, description="Memory in MB")
    disk: int = Field(default=20, ge=10, description="Disk size in GB")
    network: str = Field(default="default", description="Network name")
    environment: str = Field(default="production", description="Environment: production, staging, dev")
    variables: Optional[Dict[str, Any]] = Field(default=None, description="Additional cloud-init variables")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "web-prod-01",
                "template": "webserver",
                "os_type": "alpine",
                "cpu": 4,
                "memory": 4096,
                "disk": 20,
                "network": "default",
                "environment": "production",
                "variables": {
                    "app_port": 8080,
                    "domain": "example.com"
                }
            }
        }
    }

class ContainerDeployRequest(BaseModel):
    """Request model for container deployment"""
    name: str = Field(..., description="Service name")
    image: str = Field(..., description="Docker image")
    replicas: int = Field(default=1, ge=1, description="Number of replicas")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    ports: List[str] = Field(default_factory=list, description="Port mappings (e.g., '80:80')")
    networks: List[str] = Field(default_factory=lambda: ["backend"], description="Networks to attach")
    labels: Optional[Dict[str, str]] = Field(default=None, description="Service labels")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "nginx-proxy",
                "image": "nginx:alpine",
                "replicas": 2,
                "environment": {
                    "NGINX_HOST": "example.com",
                    "NGINX_PORT": "80"
                },
                "ports": ["80:80", "443:443"],
                "networks": ["backend"],
                "labels": {
                    "traefik.enable": "true"
                }
            }
        }
    }


class DeploymentResponse(BaseModel):
    """Response model for deployment operations"""
    success: bool
    deployment_id: Optional[int] = None
    resource_id: Optional[str] = None
    message: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "deployment_id": 123,
                "resource_id": "vm-ref-12345",
                "message": "VM web-prod-01 deployed successfully"
            }
        }
    }


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    timestamp: str
    services: Dict[str, str]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "timestamp": "2025-01-17T10:30:00Z",
                "services": {
                    "gitea": "up",
                    "xenserver": "up",
                    "docker_swarm": "up",
                    "database": "up"
                }
            }
        }
    }


class Deployment(BaseModel):
    """Deployment record"""
    id: int
    type: str
    name: str
    config: Dict[str, Any]
    resource_ref: Optional[str]
    status: str
    error: Optional[str]
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
    id: int
    block_number: int
    previous_hash: Optional[str]
    current_hash: str
    deployment_type: str
    name: str
    config: Dict[str, Any]
    resource_ref: Optional[str]
    status: str
    error: Optional[str]
    source_ip: Optional[str]
    source_country: Optional[str]
    created_at: datetime

    model_config = {
        "json_schema_extra": {
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
                "created_at": "2025-01-17T10:30:00Z"
            }
        }
    }


class BlockchainVerifyResponse(BaseModel):
    """Response model for blockchain verification"""
    valid: bool
    blocks_checked: int
    message: Optional[str] = None
    error: Optional[str] = None
    invalid_blocks: Optional[List[Dict[str, Any]]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "valid": True,
                "blocks_checked": 150,
                "message": "Chain integrity verified",
                "error": None,
                "invalid_blocks": None
            }
        }
    }


class BlockListResponse(BaseModel):
    """Response model for blockchain blocks list"""
    success: bool
    count: int
    blocks: List[BlockchainBlock]

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "count": 10,
                "blocks": []
            }
        }
    }
