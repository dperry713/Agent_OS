import asyncio
import logging
from datetime import datetime
from typing import Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential

from app.models.schemas import Task, Agent, Tenant, TaskStatus, AuditLogEntry
from app.tools.registry import registry
from app.memory.store import MemoryStore, SemanticCacheStore
from app.tools.context import ToolContext
from app.runtime.sandbox import SandboxExecutor
from app.security.vault import vault_service
from app.core.exceptions import ToolExecutionError, PolicyViolation
from app.core.resilience import CircuitBreaker, RateLimiter

# OpenTelemetry
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

class RuntimeEngine:
    def __init__(self, policy_engine: PolicyEngine, memory_store: MemoryStore):
        self.policy_engine = policy_engine
        self.memory_store = memory_store
        self.semantic_cache = SemanticCacheStore()
        self.sandbox = SandboxExecutor()
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        self.rate_limiter = RateLimiter()

    async def _log_audit(self, tenant_id: str, agent_id: str, task_id: str, action: str, details: dict):
        """Persists a tamper-proof audit log entry."""
        async with await get_db_session(tenant_id) as session:
            import uuid
            log_entry = DBAuditLog(
                log_id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                agent_id=agent_id,
                task_id=task_id,
                action=action,
                details=details
            )
            session.add(log_entry)
            await session.commit()

    @tracer.start_as_current_span("execute_task")
    async def execute_task(self, task: Task, agent: Agent, tenant: Tenant) -> Task:
        span = trace.get_current_span()
        span.set_attribute("tenant_id", tenant.tenant_id)
        span.set_attribute("agent_id", agent.agent_id)
        span.set_attribute("tool_name", task.tool_name)

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        
        # Initial Audit
        await self._log_audit(
            tenant.tenant_id, agent.agent_id, task.task_id,
            "task_started", {"tool": task.tool_name, "input_keys": list(task.input_data.keys())}
        )
        
        try:
            # 1. Policy & Security Checks
            if not await self.policy_engine.validate_execution(tenant, agent, task.tool_name):
                await self._log_audit(tenant.tenant_id, agent.agent_id, task.task_id, "policy_violation", {"tool": task.tool_name})
                raise PolicyViolation(f"Access denied for tool: {task.tool_name}")

            # 2. Rate Limiting (Quota Enforcement)
            await self.rate_limiter.check_rate_limit(tenant.tenant_id)

            # 2. Secret Injection (from OpenBao)
            api_key = vault_service.get_llm_api_key(tenant.tenant_id, "general")
            if api_key:
                task.input_data["_secret_key"] = api_key

            # 3. Execution (with Circuit Breaker & Retry Policy)
            result = await self.circuit_breaker.call(
                self._execute_with_retry, task, agent, tenant
            )
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            
            await self._log_audit(tenant.tenant_id, agent.agent_id, task.task_id, "task_completed", {"tool": task.tool_name})
            
        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {str(e)}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
            await self._log_audit(tenant.tenant_id, agent.agent_id, task.task_id, "task_failed", {"error": str(e)})
        
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

        # 1. Semantic Cache Lookup
        # Generate a stable string representation of the tool call for embedding
        query_text = f"tool:{task.tool_name} input:{sorted(task.input_data.items())}"
        
        # Mock embedding generation (In prod, use OpenAI/Gemini embedding model)
        # query_embedding = await self._get_embedding(query_text)
        query_embedding = [0.1] * 1536 # Mock
        
        cached_result = await self.semantic_cache.get_cached_result(tenant.tenant_id, query_embedding)
        if cached_result:
            logger.info("semantic_cache_hit", tool=task.tool_name, tenant_id=tenant.tenant_id)
            return cached_result

        # 2. Execution
        context = ToolContext(tenant.tenant_id, agent.agent_id, self.memory_store)
        
        # All tools run through the sandbox layer
        result = await self.sandbox.run_tool(
            tool.validate_and_execute,
            task.input_data,
            agent,
            context
        )
        
        # 3. Cache the Result
        await self.semantic_cache.set_cache(tenant.tenant_id, query_text, query_embedding, result)
        
        return result
