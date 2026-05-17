from .celery_app import app
from app.runtime.engine import RuntimeEngine
from app.policy.engine import PolicyEngine
from app.memory.store import MemoryStore
from app.models.schemas import Task, Agent, Tenant
from app.models.db import DBTask
from app.core.db import get_db_session
from sqlalchemy import update
import asyncio

# Setup singleton-like engines for worker use
policy_engine = PolicyEngine()
memory_store = MemoryStore()
runtime_engine = RuntimeEngine(policy_engine, memory_store)

async def _run_task_async(task: Task, agent: Agent, tenant: Tenant):
    # Execute the task
    updated_task = await runtime_engine.execute_task(task, agent, tenant)
    
    # Persist the update to PostgreSQL
    async with await get_db_session(tenant.tenant_id) as session:
        await session.execute(
            update(DBTask)
            .where(DBTask.task_id == updated_task.task_id)
            .values(
                status=updated_task.status,
                result=updated_task.result,
                error=updated_task.error,
                started_at=updated_task.started_at,
                finished_at=updated_task.finished_at
            )
        )
        await session.commit()
    
    return updated_task

@app.task(name="app.kernel.tasks.execute_agent_task")
def execute_agent_task(task_dict: dict, agent_dict: dict, tenant_dict: dict):
    """
    Celery task that wraps the agent execution loop.
    """
    # Re-hydrate models
    task = Task(**task_dict)
    agent = Agent(**agent_dict)
    tenant = Tenant(**tenant_dict)

    # Run the async execution logic in a synchronous Celery worker context
    loop = asyncio.get_event_loop()
    updated_task = loop.run_until_complete(
        _run_task_async(task, agent, tenant)
    )
    
    return updated_task.dict()
