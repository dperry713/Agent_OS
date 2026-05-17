from .celery_app import app
from app.runtime.engine import RuntimeEngine
from app.policy.engine import PolicyEngine
from app.memory.store import MemoryStore
from app.models.schemas import Task, Agent, Tenant, TaskStatus
from app.models.db import DBTask
from app.kernel.registry import system_registry
from app.core.db import get_db_session
from sqlalchemy import update
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

# Singletons for worker performance
policy_engine = PolicyEngine()
memory_store = MemoryStore()
runtime_engine = RuntimeEngine(policy_engine, memory_store)

async def _execute_task_async(task_id: str, tenant_id: str, agent_id: str, tool_name: str, input_data: dict):
    # RLS is handled by get_db_session(tenant_id)
    async with await get_db_session(tenant_id) as session:
        # 1. Initialize Task Record with Idempotency Check
        existing_task = await session.get(DBTask, task_id)
        if existing_task:
            if existing_task.status in [TaskStatus.COMPLETED, TaskStatus.RUNNING]:
                logger.warning(f"Task {task_id} already in state {existing_task.status}. Skipping.")
                return existing_task.result

        if not existing_task:
            db_task = DBTask(
                task_id=task_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                tool_name=tool_name,
                input_data=input_data,
                status=TaskStatus.RUNNING,
                started_at=datetime.utcnow(),
                version=1
            )
            session.add(db_task)
            await session.commit()
        else:
            # Atomic update to RUNNING with version check
            result = await session.execute(
                update(DBTask)
                .where(DBTask.task_id == task_id)
                .where(DBTask.version == existing_task.version)
                .values(status=TaskStatus.RUNNING, started_at=datetime.utcnow(), version=DBTask.version + 1)
            )
            if result.rowcount == 0:
                raise Exception("Optimistic locking failure: Task updated by another worker.")
            await session.commit()

        # 2. Fetch Context
        tenant = await system_registry.get_tenant(tenant_id)
        agent = await system_registry.get_agent(tenant_id, agent_id)

        # 3. Execution
        try:
            task_obj = Task(
                task_id=task_id, tenant_id=tenant_id, agent_id=agent_id,
                tool_name=tool_name, input_data=input_data
            )
            updated_task = await runtime_engine.execute_task(task_obj, agent, tenant)
            
            # 4. Final Persist with version increment
            current_task = await session.get(DBTask, task_id)
            await session.execute(
                update(DBTask)
                .where(DBTask.task_id == task_id)
                .where(DBTask.version == current_task.version)
                .values(
                    status=updated_task.status,
                    result=updated_task.result,
                    error=updated_task.error,
                    finished_at=updated_task.finished_at,
                    version=DBTask.version + 1
                )
            )
            await session.commit()
            return updated_task.dict()

        except Exception as e:
            logger.exception(f"Fatal error in task {task_id}")
            current_task = await session.get(DBTask, task_id)
            await session.execute(
                update(DBTask)
                .where(DBTask.task_id == task_id)
                .where(DBTask.version == current_task.version)
                .values(
                    status=TaskStatus.FAILED, 
                    error=str(e), 
                    finished_at=datetime.utcnow(),
                    version=DBTask.version + 1
                )
            )
            await session.commit()
            raise

@app.task(name="app.kernel.tasks.execute_agent_task", bind=True, max_retries=3)
def execute_agent_task(self, task_id: str, tenant_id: str, agent_id: str, tool_name: str, input_data: dict):
    """Celery entry point for agent execution."""
    loop = asyncio.get_event_loop()
    try:
        return loop.run_until_complete(
            _execute_task_async(task_id, tenant_id, agent_id, tool_name, input_data)
        )
    except Exception as exc:
        # Automatic retry for transient failures
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
