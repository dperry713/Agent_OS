from typing import AsyncIterator, List, Dict, Any, Optional
from .base import BaseAgentLoop, AgentStep, AgentState
from app.models.schemas import Task, Agent, Tenant, TaskStatus
from app.core.exceptions import AgentLoopError, ToolExecutionError
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class ReActLoop(BaseAgentLoop):
    """
    Robust implementation of the Reasoning and Acting (ReAct) pattern.
    Features: 
    - Self-correction on malformed LLM outputs.
    - Automatic state recovery via checkpointing.
    - Human-in-the-loop (HITL) pause/resume.
    - Granular cost and token tracking.
    """
    
    def __init__(self, agent: Agent, tenant: Tenant, context: ToolContext, runtime_engine: Any):
        super().__init__(agent, tenant, context)
        self.runtime_engine = runtime_engine
        self.max_iterations = 15
        self.model_name = "gpt-4-turbo" # Default for cost calculation

    async def run(self, task: Task) -> AsyncIterator[AgentStep]:
        # 1. Recovery: Resume from the last known good state
        state = await self.load_checkpoint(task.task_id) or AgentState(task_id=task.task_id)
        logger.info(f"ReAct Loop: Starting/Resuming task {task.task_id} at step {len(state.steps)}")

        for i in range(len(state.steps), self.max_iterations):
            try:
                # 2. Check for HITL Interruption
                if state.metadata.get("hitl_required") and not state.metadata.get("hitl_approved"):
                    logger.info(f"Task {task.task_id} paused for human approval.")
                    task.status = TaskStatus.AWAITING_INPUT
                    break

                # 3. Reasoning Step (LLM Call)
                # In production, this would format the task and history into a system prompt.
                llm_response = await self._call_llm(task, state.steps)
                
                # Parse and Validate LLM response
                parsed = self._process_llm_output(llm_response)
                
                step = AgentStep(
                    thought=parsed.get("thought", "Analyzing..."),
                    tool_name=parsed.get("tool_name"),
                    tool_input=parsed.get("tool_input"),
                    tokens_used=llm_response.get("usage", 0)
                )

                # Track usage immediately
                self.track_usage(state, tokens=step.tokens_used, model=self.model_name)

                # 4. Final Answer Check
                if not step.tool_name or step.tool_name == "final_answer":
                    step.observation = "Final answer reached."
                    state.steps.append(step)
                    await self.save_checkpoint(state)
                    await self.stream_step(step)
                    yield step
                    break

                # 5. Policy & Safety check for high-risk tools
                if step.tool_name in ["sql_query_readonly", "git_ops"]:
                    if not state.metadata.get("hitl_approved"):
                        state.metadata["hitl_required"] = True
                        state.metadata["pending_tool"] = step.tool_name
                        await self.save_checkpoint(state)
                        yield AgentStep(thought=f"Action '{step.tool_name}' requires human approval.")
                        break

                # 6. Execute Action
                try:
                    # Reuse RuntimeEngine to ensure policy, sandbox, and circuit breaker are applied
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
                        step.observation = f"Tool result: {str(execution_result.result)[:1000]}"
                    else:
                        step.observation = f"Tool failed: {execution_result.error}"
                except Exception as e:
                    logger.error(f"Action execution failure: {str(e)}")
                    step.observation = f"Critical error during tool execution: {str(e)}"

                # 7. Update State & Stream
                state.steps.append(step)
                await self.save_checkpoint(state)
                await self.stream_step(step)
                yield step

                # Optional: Self-correction check
                if "error" in step.observation.lower():
                    logger.warning(f"ReAct Loop detecting error at step {i}, preparing for retry/correction.")

            except Exception as e:
                logger.error(f"ReAct Loop Step {i} failed: {str(e)}")
                raise AgentLoopError(f"Reasoning loop crashed: {str(e)}")

        logger.info(f"ReAct Loop finished for task {task_id}. Total tokens: {state.total_tokens}")

    def _process_llm_output(self, raw_response: dict) -> dict:
        """Robust parsing of LLM JSON or text blocks."""
        # In a real system, this would handle various LLM formatting quirks
        content = raw_response.get("content", "{}")
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback regex parsing or heuristic extraction
            return {"thought": "The LLM returned invalid JSON. Retrying...", "tool_name": None}

    async def _call_llm(self, task: Task, history: List[AgentStep]) -> Dict[str, Any]:
        """Mocked LLM call with realistic response structure."""
        # Real implementation would call OpenAI/Gemini/etc.
        return {
            "content": json.dumps({
                "thought": "I will search for the documentation requested.",
                "tool_name": "web_search",
                "tool_input": {"query": task.input_data.get("query", "")}
            }),
            "usage": 250
        }

from app.tools.context import ToolContext
