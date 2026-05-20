from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class TaskBase(BaseModel):
    agent_id: str
    payload: Dict[str, Any] = {}

class TaskCreate(TaskBase):
    pass

class TaskResponse(TaskBase):
    id: str
    tenant_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}