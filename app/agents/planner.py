from typing import AsyncIterator, List, Dict, Any
from .base import BaseAgentLoop, AgentStep, AgentState
from app.models.schemas import Task, Agent, Tenant, TaskStatus
import logging

logger = logging.getLogger(__name__)

class PlanAndExecuteLoop(BaseAgentLoop):
    """
    Plan-and-Execute pattern.
    First decomposes the task into a series of steps, then executes them.
    Suitable for complex tasks requiring long-term consistency.
    """
    
    def __init__(self, agent: Agent, tenant: Tenant, context: ToolContext, runtime_engine: Any):
        super().__init__(agent, tenant, context)
        self.runtime_engine = runtime_engine

    async def run(self, task: Task) -> AsyncIterator[AgentStep]:
        state = await self.load_checkpoint(task.task_id) or AgentState(task_id=task.task_id)
        
        # 1. Generate Plan if not exists
        if "plan" not in state.metadata:
            plan = await self._generate_plan(task)
            state.metadata["plan"] = plan
            state.metadata["current_step_idx"] = 0
            await self.save_checkpoint(state)

        plan = state.metadata["plan"]
        start_idx = state.metadata.get("current_step_idx", 0)

        for i in range(start_idx, len(plan)):
            plan_item = plan[i]
            
            step = AgentStep(
                thought=f"Executing step {i+1}/{len(plan)}: {plan_item['description']}",
                tool_name=plan_item.get("tool_name"),
                tool_input=plan_item.get("tool_input")
            )

            # 2. Execute Step
            try:
                sub_task = Task(
                    task_id=f"{task.task_id}_{i}",
                    agent_id=self.agent.agent_id,
                    tenant_id=self.tenant.tenant_id,
                    tool_name=step.tool_name,
                    input_data=step.tool_input or {}
                )
                execution_result = await self.runtime_engine.execute_task(
                    sub_task, self.agent, self.tenant
                )
                step.tool_output = execution_result.result if execution_result.status == TaskStatus.COMPLETED else execution_result.error
            except Exception as e:
                step.tool_output = f"Error: {str(e)}"

            state.steps.append(step)
            state.metadata["current_step_idx"] = i + 1
            await self.save_checkpoint(state)
            yield step

    async def _generate_plan(self, task: Task) -> List[Dict[str, Any]]:
        """Mock plan generation."""
        return [
            {"description": "Search for latest AI news", "tool_name": "web_search", "tool_input": {"query": "AI news May 2026"}},
            {"description": "Summarize findings", "tool_name": "python_repl", "tool_input": {"code": "print('Summary of AI news...')"}}
        ]

from app.tools.context import ToolContext
