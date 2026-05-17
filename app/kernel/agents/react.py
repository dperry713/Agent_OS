from typing import AsyncIterator, List, Dict, Any, Optional
from .base import BaseAgentLoop, AgentStep, AgentState
from app.models.schemas import Task, Agent, Tenant, TaskStatus
from app.tools.registry import registry
from app.runtime.sandbox import SandboxExecutor
import logging

logger = logging.getLogger(__name__)

class ReActLoop(BaseAgentLoop):
    """
    Implementation of the Reasoning and Acting (ReAct) pattern.
    Iteratively generates thoughts, selects tools, and processes observations.
    """
    
    def __init__(self, agent: Agent, tenant: Tenant, context: ToolContext, runtime_engine: Any):
        super().__init__(agent, tenant, context)
        self.runtime_engine = runtime_engine
        self.max_iterations = 10

    async def run(self, task: Task) -> AsyncIterator[AgentStep]:
        state = await self.load_checkpoint(task.task_id) or AgentState(task_id=task.task_id)
        
        for i in range(len(state.steps), self.max_iterations):
            # 1. Generate Reasoning & Action (Mock LLM Call)
            # In a real system, this would call an LLM with the task and history.
            llm_response = await self._call_llm(task, state.steps)
            
            step = AgentStep(
                thought=llm_response.get("thought", ""),
                tool_name=llm_response.get("tool_name"),
                tool_input=llm_response.get("tool_input")
            )

            # 2. Check for Completion
            if not step.tool_name or step.tool_name == "final_answer":
                yield step
                break

            # 3. Execute Tool via RuntimeEngine (respecting Sandbox and Policy)
            try:
                # We reuse the RuntimeEngine logic for consistency
                # Note: RuntimeEngine expects a Task object, so we create a sub-task or mock it
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
                step.tool_output = f"Error executing tool: {str(e)}"

            state.steps.append(step)
            await self.save_checkpoint(state)
            yield step

            if "final_answer" in str(step.tool_output):
                break

    async def _call_llm(self, task: Task, history: List[AgentStep]) -> Dict[str, Any]:
        """Placeholder for actual LLM integration."""
        # This would use the injected API keys from Vault via RuntimeEngine
        return {
            "thought": "I need to search for the current weather to answer the user.",
            "tool_name": "web_search",
            "tool_input": {"query": "weather in San Francisco"}
        }

from app.tools.context import ToolContext
