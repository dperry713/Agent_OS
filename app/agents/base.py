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
    """Represents a single step in an agent loop."""
    thought: str
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AgentState(BaseModel):
    """Persistent state for an agent loop (used for checkpointing)."""
    task_id: str
    steps: List[AgentStep] = []
    metadata: Dict[str, Any] = {}
    total_tokens: int = 0
    total_cost: float = 0.0

class BaseAgentLoop(ABC):
    """
    Abstract base class for iterative agent execution patterns.
    Handles state persistence, memory integration, and lifecycle management.
    """
    
    def __init__(self, agent: Agent, tenant: Tenant, context: ToolContext):
        self.agent = agent
        self.tenant = tenant
        self.context = context

    @abstractmethod
    async def run(self, task: Task) -> AsyncIterator[AgentStep]:
        """
        Executes the agent loop for a given task.
        Yields steps for streaming support.
        """
        pass

    async def stream_step(self, step: AgentStep):
        """Publishes the current step to Valkey for real-time streaming."""
        client = valkey_async.from_url(settings.VALKEY_URL)
        await client.publish(f"task_stream:{self.agent.task_id}", step.model_dump_json())
        await client.close()

    async def save_checkpoint(self, state: AgentState):
        """Saves the current agent state to Valkey/Postgres for recovery or HITL."""
        state_json = state.model_dump_json()
        await self.context.set_memory(f"checkpoint:{state.task_id}", state_json)
        logger.info(f"Checkpoint saved for task {state.task_id}")

    async def load_checkpoint(self, task_id: str) -> Optional[AgentState]:
        """Loads a previously saved state."""
        state_json = await self.context.get_memory(f"checkpoint:{task_id}")
        if state_json:
            return AgentState.model_validate_json(state_json)
        return None

    def track_usage(self, state: AgentState, tokens: int, model: str):
        """Updates cost and token tracking."""
        # Simple placeholder for cost calculation
        costs = {"gpt-4": 0.03 / 1000, "gemini-1.5-pro": 0.0035 / 1000}
        rate = costs.get(model, 0.0)
        state.total_tokens += tokens
        state.total_cost += (tokens * rate)
