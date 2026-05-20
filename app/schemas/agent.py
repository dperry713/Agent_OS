from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class AgentBase(BaseModel):
    name: str
    configuration: Dict[str, Any] = {}

class AgentCreate(AgentBase):
    pass

class AgentResponse(AgentBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}