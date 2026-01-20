from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

from .models.database import Base, Deployment, DeploymentStatus, DeploymentType

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")
    
    @contextmanager
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    async def create_deployment(self, deployment_type: str, name: str, config: Dict) -> int:
        with self.get_session() as session:
            deployment = Deployment(
                deployment_type=DeploymentType[deployment_type.upper()],
                name=name,
                status=DeploymentStatus.PENDING,
                config=config
            )
            session.add(deployment)
            session.flush()
            return deployment.id
    
    async def update_deployment_status(self, deployment_id: int, status: str, error: Optional[str] = None):
        with self.get_session() as session:
            deployment = session.query(Deployment).filter(Deployment.id == deployment_id).first()
            if deployment:
                deployment.status = DeploymentStatus[status.upper()]
                if error:
                    deployment.error_message = error
                if status == "in_progress":
                    deployment.started_at = datetime.utcnow()
                elif status in ["completed", "failed"]:
                    deployment.completed_at = datetime.utcnow()
    
    async def get_deployment(self, deployment_id: int):
        with self.get_session() as session:
            return session.query(Deployment).filter(Deployment.id == deployment_id).first()
    
    async def list_deployments(self, limit: int = 20, offset: int = 0) -> List[Deployment]:
        with self.get_session() as session:
            return session.query(Deployment).order_by(Deployment.created_at.desc()).offset(offset).limit(limit).all()
    
    async def get_deployment_stats(self, days: int = 30) -> Dict[str, Any]:
        # Implementation
        return {"total": 0, "completed": 0, "failed": 0}

db_manager: Optional[DatabaseManager] = None

def init_db(database_url: str):
    global db_manager
    db_manager = DatabaseManager(database_url)
    db_manager.create_tables()

def get_db_manager() -> DatabaseManager:
    if db_manager is None:
        raise RuntimeError("Database not initialized")
    return db_manager

