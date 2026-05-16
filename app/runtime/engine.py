import asyncio
from typing import Optional, Any
from app.models.schemas import Task, Agent, Tenant, TaskStatus, AuditLogEntry
from app.tools.registry import registry
from app.policy.engine import PolicyEngine
from app.memory.store import MemoryStore
from datetime import datetime

from app.tools.context import ToolContext

class RuntimeEngine:
    def __init__(self, policy_engine: PolicyEngine, memory_store: MemoryStore):
        self.policy_engine = policy_engine
        self.memory_store = memory_store

    async def execute_task(self, task: Task, agent: Agent, tenant: Tenant) -> Task:
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        
        # 1. Validate Policy
        allowed = await self.policy_engine.validate_execution(tenant, agent, task.tool_name)
        if not allowed:
            task.status = TaskStatus.FAILED
            task.error = f"Policy violation: {task.tool_name} is not allowed."
            task.finished_at = datetime.utcnow()
            return task

        # 2. Get Tool
        tool = registry.get_tool(task.tool_name)
        if not tool:
            task.status = TaskStatus.FAILED
            task.error = f"Tool '{task.tool_name}' not found."
            task.finished_at = datetime.utcnow()
            return task

        # 3. Create Context
        context = ToolContext(tenant.tenant_id, agent.agent_id, self.memory_store)

        # 4. Execute Tool
        try:
            result = await tool.execute(task.input_data, agent, context)
            task.result = result
            task.status = TaskStatus.COMPLETED
            
            # Log Audit
            self.policy_engine.log_audit(AuditLogEntry(
                tenant_id=tenant.tenant_id,
                agent_id=agent.agent_id,
                task_id=task.task_id,
                tool=task.tool_name,
                status="success",
                result=result
            ))
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.policy_engine.log_audit(AuditLogEntry(
                tenant_id=tenant.tenant_id,
                agent_id=agent.agent_id,
                task_id=task.task_id,
                tool=task.tool_name,
                status="failed",
                error=str(e)
            ))
        
        task.finished_at = datetime.utcnow()
        return task
