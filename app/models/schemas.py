from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_INPUT = "awaiting_input"

class Tenant(BaseModel):
    tenant_id: str
    name: str
    max_agents: int = 10
    max_concurrent_tasks: int = 5
    blocked_tools: List[str] = []
    custom_routing_key: Optional[str] = None

class Agent(BaseModel):
    agent_id: str
    tenant_id: str
    name: str
    metadata: Dict[str, Any] = {}

class Task(BaseModel):
    task_id: str
    agent_id: str
    tenant_id: str
    tool_name: str
    input_data: Dict[str, Any]
    status: TaskStatus = TaskStatus.QUEUED
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

class AuditLogEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: str
    agent_id: str
    task_id: str
    tool: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
