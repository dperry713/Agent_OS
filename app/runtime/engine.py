import asyncio
import logging
from datetime import datetime
from typing import Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential

from app.models.schemas import Task, Agent, Tenant, TaskStatus, AuditLogEntry
from app.tools.registry import registry
from app.policy.engine import PolicyEngine
from app.memory.store import MemoryStore
from app.tools.context import ToolContext
from app.runtime.sandbox import SandboxExecutor
from app.security.vault import vault_service
from app.core.exceptions import ToolExecutionError, PolicyViolation

# OpenTelemetry
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

class RuntimeEngine:
    def __init__(self, policy_engine: PolicyEngine, memory_store: MemoryStore):
        self.policy_engine = policy_engine
        self.memory_store = memory_store
        self.sandbox = SandboxExecutor()

    @tracer.start_as_current_span("execute_task")
    async def execute_task(self, task: Task, agent: Agent, tenant: Tenant) -> Task:
        span = trace.get_current_span()
        span.set_attribute("tenant_id", tenant.tenant_id)
        span.set_attribute("agent_id", agent.agent_id)
        span.set_attribute("tool_name", task.tool_name)

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        
        try:
            # 1. Policy & Security Checks
            if not await self.policy_engine.validate_execution(tenant, agent, task.tool_name):
                raise PolicyViolation(f"Access denied for tool: {task.tool_name}")

            # 2. Secret Injection (from OpenBao)
            api_key = vault_service.get_llm_api_key(tenant.tenant_id, "general")
            if api_key:
                task.input_data["_secret_key"] = api_key

            # 3. Execution (with Retry Policy)
            result = await self._execute_with_retry(task, agent, tenant)
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            
        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {str(e)}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
        
        task.finished_at = datetime.utcnow()
        return task

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _execute_with_retry(self, task: Task, agent: Agent, tenant: Tenant):
        tool = registry.get_tool(task.tool_name)
        if not tool:
            raise ToolExecutionError(f"Tool {task.tool_name} not found.")

        context = ToolContext(tenant.tenant_id, agent.agent_id, self.memory_store)
        
        # All tools run through the sandbox layer
        return await self.sandbox.run_tool(
            tool.validate_and_execute,
            task.input_data,
            agent,
            context
        )
