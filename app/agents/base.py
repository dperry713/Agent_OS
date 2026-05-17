from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator
from pydantic import BaseModel, Field
from app.models.schemas import Task, Agent, Tenant, TaskStatus
from app.tools.context import ToolContext
from datetime import datetime
import valkey.asyncio as valkey_async
from app.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)

class AgentStep(BaseModel):
    """Represents a single granular step in an agent reasoning loop."""
    thought: str
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Any] = None
    observation: Optional[str] = None
    tokens_used: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AgentState(BaseModel):
    """Persistent state for an agent loop, used for checkpointing and recovery."""
    task_id: str
    steps: List[AgentStep] = []
    metadata: Dict[str, Any] = {}
    total_tokens: int = 0
    total_cost: float = 0.0
    status: TaskStatus = TaskStatus.RUNNING
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class BaseAgentLoop(ABC):
    """
    Abstract base class for high-reliability agent execution patterns.
    Handles memory integration, state persistence, and real-time streaming.
    """
    
    def __init__(self, agent: Agent, tenant: Tenant, context: ToolContext):
        self.agent = agent
        self.tenant = tenant
        self.context = context

    @abstractmethod
    async def run(self, task: Task) -> AsyncIterator[AgentStep]:
        """
        Executes the specialized reasoning loop.
        Yields steps for real-time visibility.
        """
        pass

    async def stream_step(self, task_id: str, step: AgentStep):
        """Publishes progress chunks to Valkey for WebSocket subscribers."""
        try:
            client = valkey_async.from_url(settings.VALKEY_URL)
            await client.publish(f"task_stream:{task_id}", step.model_dump_json())
            await client.close()
        except Exception as e:
            logger.warning(f"Streaming failed for task {task_id}: {str(e)}")

    async def save_checkpoint(self, state: AgentState):
        """Persists intermediate state to the tenant's isolated state layer."""
        state.last_updated = datetime.utcnow()
        state_json = state.model_dump_json()
        await self.context.set_memory(f"checkpoint:{state.task_id}", state_json)
        logger.info(f"Checkpoint saved: Task {state.task_id}, Steps: {len(state.steps)}")

    async def load_checkpoint(self, task_id: str) -> Optional[AgentState]:
        """Recovers state from the state layer."""
        state_json = await self.context.get_memory(f"checkpoint:{task_id}")
        if state_json:
            return AgentState.model_validate_json(state_json)
        return None

    def track_usage(self, state: AgentState, tokens: int, model: str):
        """Calculates and aggregates cost based on provider pricing."""
        # Baseline pricing per 1k tokens
        pricing = {
            "gpt-4-turbo": 0.01, 
            "gemini-1.5-pro": 0.0035,
            "claude-3-opus": 0.015
        }
        rate = pricing.get(model, 0.01)
        state.total_tokens += tokens
        state.total_cost += (tokens / 1000.0) * rate
