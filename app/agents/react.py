from typing import AsyncIterator, List, Dict, Any, Optional
from .base import BaseAgentLoop, AgentStep, AgentState
from app.models.schemas import Task, Agent, Tenant, TaskStatus
from app.core.exceptions import AgentLoopError
import logging

logger = logging.getLogger(__name__)

class ReActLoop(BaseAgentLoop):
    """
    Robust ReAct Loop with Error Recovery, HITL, and Checkpointing.
    """
    
    def __init__(self, agent: Agent, tenant: Tenant, context: ToolContext, runtime_engine: Any):
        super().__init__(agent, tenant, context)
        self.runtime_engine = runtime_engine
        self.max_iterations = 15

    async def run(self, task: Task) -> AsyncIterator[AgentStep]:
        # 1. Recovery: Load from checkpoint if exists
        state = await self.load_checkpoint(task.task_id) or AgentState(task_id=task.task_id)
        
        # 2. Main Loop
        for i in range(len(state.steps), self.max_iterations):
            try:
                # HITL Check
                if state.metadata.get("awaiting_approval"):
                    yield AgentStep(thought="Awaiting human approval before proceeding.")
                    break

                # Reasoning Step
                llm_response = await self._call_llm(task, state.steps)
                
                step = AgentStep(
                    thought=llm_response.get("thought", "Analyzing next step..."),
                    tool_name=llm_response.get("tool_name"),
                    tool_input=llm_response.get("tool_input")
                )

                # Final Answer Check
                if not step.tool_name or step.tool_name == "final_answer":
                    state.steps.append(step)
                    await self.save_checkpoint(state)
                    await self.stream_step(step)
                    yield step
                    break

                # Execute Action via RuntimeEngine (includes Sandbox & Circuit Breaker)
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
                
                if execution_result.status == TaskStatus.COMPLETED:
                    step.tool_output = execution_result.result
                else:
                    step.tool_output = f"Error: {execution_result.error}"

                # Update State & Checkpoint
                state.steps.append(step)
                await self.save_checkpoint(state)
                await self.stream_step(step)
                yield step

            except Exception as e:
                logger.error(f"ReAct Loop Failure: {str(e)}")
                raise AgentLoopError(f"Critical loop failure: {str(e)}")

    async def _call_llm(self, task: Task, history: List[AgentStep]) -> Dict[str, Any]:
        """Mock LLM interaction with context awareness."""
        return {
            "thought": "I need to check the database status.",
            "tool_name": "sql_query_readonly",
            "tool_input": {"query": "SELECT status FROM system_checks"}
        }

from app.tools.context import ToolContext
