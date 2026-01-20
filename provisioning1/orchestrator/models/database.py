from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class DeploymentStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class DeploymentType(enum.Enum):
    VM = "vm"
    CONTAINER = "container"
    SWARM_SERVICE = "swarm_service"

class Deployment(Base):
    __tablename__ = "deployments"
    
    id = Column(Integer, primary_key=True, index=True)
    deployment_type = Column(SQLEnum(DeploymentType), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(SQLEnum(DeploymentStatus), default=DeploymentStatus.PENDING)
    config = Column(JSON, nullable=False)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

