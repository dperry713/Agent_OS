import asyncio
from typing import Optional, Any
from app.models.schemas import Task, Agent, Tenant, TaskStatus, AuditLogEntry
from app.tools.registry import registry
from app.policy.engine import PolicyEngine
from app.memory.store import MemoryStore
from datetime import datetime

from app.tools.context import ToolContext
from app.runtime.sandbox import SandboxExecutor, SandboxLimits
from app.kernel.agents.react import ReActLoop
from app.kernel.agents.planner import PlanAndExecuteLoop
from app.kernel.agents.supervisor import SupervisorLoop

from app.security.vault import vault_service

class RuntimeEngine:
    def __init__(self, policy_engine: PolicyEngine, memory_store: MemoryStore):
        self.policy_engine = policy_engine
        self.memory_store = memory_store
        self.sandbox = SandboxExecutor()

    async def execute_task(self, task: Task, agent: Agent, tenant: Tenant) -> Task:
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        
        # 0. Dynamic Secret Injection
        api_key = vault_service.get_llm_api_key(tenant.tenant_id, "google")
        if api_key:
            task.input_data["api_key"] = api_key 

        # 3. Create Context
        context = ToolContext(tenant.tenant_id, agent.agent_id, self.memory_store)

        # Check for Agent Loop Pattern
        loop_type = task.input_data.get("loop_type")
        if loop_type:
            return await self._run_agent_loop(loop_type, task, agent, tenant, context)
        
        # Standard Single Tool Execution
        return await self._execute_single_tool(task, agent, tenant, context)

    async def _run_agent_loop(self, loop_type: str, task: Task, agent: Agent, tenant: Tenant, context: ToolContext) -> Task:
        loops = {
            "react": ReActLoop,
            "plan_and_execute": PlanAndExecuteLoop,
            "supervisor": SupervisorLoop
        }
        
        loop_cls = loops.get(loop_type)
        if not loop_cls:
            task.status = TaskStatus.FAILED
            task.error = f"Unknown loop type: {loop_type}"
            return task

        loop = loop_cls(agent, tenant, context, self)
        
        try:
            results = []
            async for step in loop.run(task):
                results.append(step.model_dump())
            
            task.result = results
            task.status = TaskStatus.COMPLETED
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
        
        task.finished_at = datetime.utcnow()
        return task

    async def _execute_single_tool(self, task: Task, agent: Agent, tenant: Tenant, context: ToolContext) -> Task:
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

        # 4. Execute Tool via Sandbox
        try:
            result = await self.sandbox.run_tool(
                tool.validate_and_execute, 
                task.input_data, 
                agent, 
                context
            )
            task.result = result
            task.status = TaskStatus.COMPLETED
            
            self.policy_engine.log_audit(AuditLogEntry(
                tenant_id=tenant.tenant_id, agent_id=agent.agent_id,
                task_id=task.task_id, tool=task.tool_name,
                status="success", result=result
            ))
        except TimeoutError as te:
            task.status = TaskStatus.FAILED
            task.error = f"Execution Timeout: {str(te)}"
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
        
        task.finished_at = datetime.utcnow()
        return task
