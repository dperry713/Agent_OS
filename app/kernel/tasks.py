from .celery_app import app
from app.runtime.engine import RuntimeEngine
from app.policy.engine import PolicyEngine
from app.memory.store import MemoryStore
from app.models.schemas import Task, Agent, Tenant, TaskStatus
from app.models.db import DBTask
from app.models.validation import ToolCallRequest
from app.security.vault import vault_service
from app.kernel.registry import system_registry
from app.core.db import get_db_session
from sqlalchemy import update
from datetime import datetime
import asyncio

# Setup singleton-like engines for worker use
policy_engine = PolicyEngine()
memory_store = MemoryStore()
runtime_engine = RuntimeEngine(policy_engine, memory_store)

async def _run_task_async(task_id: str, tenant_id: str, agent_id: str, tool_name: str, input_data: dict):
    # Initialize Task in DB first so we have a record
    async with await get_db_session(tenant_id) as session:
        db_task = DBTask(
            task_id=task_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            tool_name=tool_name,
            input_data=input_data,
            status=TaskStatus.QUEUED
        )
        session.add(db_task)
        await session.commit()

    # 1. Strict Pydantic Validation
    try:
        ToolCallRequest(tool_name=tool_name, input_data=input_data)
    except Exception as e:
        error_msg = f"Validation Error: {str(e)}"
        async with await get_db_session(tenant_id) as session:
            await session.execute(
                update(DBTask)
                .where(DBTask.task_id == task_id)
                .values(status=TaskStatus.FAILED, error=error_msg, finished_at=datetime.utcnow())
            )
            await session.commit()
        return {"task_id": task_id, "status": "failed", "error": error_msg}

    # 2. Get Metadata
    tenant = await system_registry.get_tenant(tenant_id)
    agent = await system_registry.get_agent(tenant_id, agent_id)
    
    if not tenant or not agent:
        error_msg = "Tenant or Agent not found"
        async with await get_db_session(tenant_id) as session:
            await session.execute(
                update(DBTask)
                .where(DBTask.task_id == task_id)
                .values(status=TaskStatus.FAILED, error=error_msg, finished_at=datetime.utcnow())
            )
            await session.commit()
        return {"task_id": task_id, "status": "failed", "error": error_msg}

    # 3. Ephemeral Secret Fetching
    api_key = vault_service.get_llm_api_key(tenant_id, "google")
    if not api_key:
        error_msg = "LLM API Key missing in Vault"
        async with await get_db_session(tenant_id) as session:
            await session.execute(
                update(DBTask)
                .where(DBTask.task_id == task_id)
                .values(status=TaskStatus.FAILED, error=error_msg, finished_at=datetime.utcnow())
            )
            await session.commit()
        return {"task_id": task_id, "status": "failed", "error": error_msg}

    # 4. Execute via Runtime Engine
    task = Task(
        task_id=task_id,
        agent_id=agent_id,
        tenant_id=tenant_id,
        tool_name=tool_name,
        input_data=input_data
    )
    
    updated_task = await runtime_engine.execute_task(task, agent, tenant)
    
    # 5. Persist results
    async with await get_db_session(tenant_id) as session:
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
    
    return updated_task.dict()

@app.task(name="app.kernel.tasks.execute_agent_task")
def execute_agent_task(task_id: str, tenant_id: str, agent_id: str, tool_name: str, input_data: dict):
    """
    Celery task that wraps the agent execution loop.
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        _run_task_async(task_id, tenant_id, agent_id, tool_name, input_data)
    )
