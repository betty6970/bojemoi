from pydantic import BaseModel
from typing import Dict, Any, Optional

class DeploymentResult(BaseModel):
    success: bool
    deployment_id: Optional[int] = None
    message: str
    metadata: Dict[str, Any] = {}

