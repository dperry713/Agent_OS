import asyncio
import uuid
from typing import Dict, List, Optional
from app.models.schemas import Task, Agent, Tenant, TaskStatus
from app.runtime.engine import RuntimeEngine
from app.core.logging import get_audit_logger

logger = get_audit_logger("kernel")

class KernelScheduler:
    def __init__(self, runtime_engine: RuntimeEngine):
        self.runtime_engine = runtime_engine
        self.tasks: Dict[str, Task] = {}
        self._queue: Optional[asyncio.Queue] = None
        self._worker_task: Optional[asyncio.Task] = None
        self._tenant_semaphores: Dict[str, asyncio.Semaphore] = {}

    @property
    def queue(self) -> asyncio.Queue:
        if self._queue is None:
            self._queue = asyncio.Queue()
        return self._queue

    async def start(self):
        current_loop = asyncio.get_running_loop()
        needs_start = False
        
        if self._worker_task is None:
            needs_start = True
        elif self._worker_task.done():
            needs_start = True
        else:
            try:
                task_loop = self._worker_task.get_loop()
                if task_loop is not current_loop:
                    logger.info("New event loop detected, recreating queue and worker.")
                    self._worker_task.cancel()
                    self._queue = asyncio.Queue() 
                    needs_start = True
            except Exception:
                needs_start = True

        if needs_start:
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info(f"Kernel Scheduler worker started on loop {id(current_loop)}.")

    async def stop(self):
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
            logger.info("Kernel Scheduler stopped.")

    async def reset(self):
        self.tasks = {}
        q = self.queue
        while not q.empty():
            try:
                q.get_nowait()
                q.task_done()
            except asyncio.QueueEmpty:
                break
        self._tenant_semaphores = {}
        logger.info("Kernel Scheduler data reset.")

    async def submit_task(self, agent: Agent, tenant: Tenant, tool_name: str, input_data: dict) -> str:
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            agent_id=agent.agent_id,
            tenant_id=tenant.tenant_id,
            tool_name=tool_name,
            input_data=input_data,
            status=TaskStatus.QUEUED
        )
        self.tasks[task_id] = task
        await self.queue.put((task_id, agent, tenant))
        logger.info(f"Task {task_id} submitted for agent {agent.agent_id}")
        return task_id

    async def _worker_loop(self):
        while True:
            try:
                task_data = await self.queue.get()
                task_id, agent, tenant = task_data
                
                if tenant.tenant_id not in self._tenant_semaphores:
                    self._tenant_semaphores[tenant.tenant_id] = asyncio.Semaphore(tenant.max_concurrent_tasks)
                
                asyncio.create_task(self._run_with_semaphore(task_id, agent, tenant))
                self.queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker Loop Error: {e}")
                await asyncio.sleep(0.1)

    async def _run_with_semaphore(self, task_id: str, agent: Agent, tenant: Tenant):
        async with self._tenant_semaphores[tenant.tenant_id]:
            task = self.tasks.get(task_id)
            if task:
                updated_task = await self.runtime_engine.execute_task(task, agent, tenant)
                self.tasks[task_id] = updated_task

    async def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    async def run_task_immediately(self, task: Task, agent: Agent, tenant: Tenant):
        updated_task = await self.runtime_engine.execute_task(task, agent, tenant)
        self.tasks[task.task_id] = updated_task
        return updated_task
