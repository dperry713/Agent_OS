import pytest
import asyncio
import time
from app.models.schemas import Tenant, Agent, TaskStatus
from app.kernel.registry import system_registry
from app.kernel.scheduler import KernelScheduler
from app.runtime.engine import RuntimeEngine
from app.policy.engine import PolicyEngine
from app.memory.store import MemoryStore
from app.tools.base import BaseTool
from app.tools.context import ToolContext
from app.tools.registry import registry
from typing import Dict, Any

class SlowTool(BaseTool):
    @property
    def name(self) -> str:
        return "slow"
    async def execute(self, input_data: Dict[str, Any], agent: Agent, context: ToolContext) -> Any:
        delay = input_data.get("delay", 0.5)
        await asyncio.sleep(delay)
        return {"done": True}

@pytest.fixture
async def stress_system():
    db_file = "stress_test.db"
    memory = MemoryStore(db_file)
    await memory.initialize()
    policy = PolicyEngine()
    runtime = RuntimeEngine(policy, memory)
    kernel = KernelScheduler(runtime)
    registry.register(SlowTool())
    await kernel.start()
    yield kernel, memory
    await kernel.stop()
    await memory.close()
    import os
    if os.path.exists(db_file): os.remove(db_file)

@pytest.mark.asyncio
async def test_concurrency_limiting(stress_system):
    kernel, _ = stress_system
    
    # Max 2 concurrent tasks
    tenant = Tenant(tenant_id="stress_t", name="Stress", max_concurrent_tasks=2)
    agent = Agent(agent_id="stress_a", tenant_id="stress_t", name="Agent")
    system_registry.register_tenant(tenant)
    system_registry.register_agent(agent)

    start_time = time.time()
    
    # Submit 4 tasks that take 0.5s each
    # With concurrency 2, total time should be ~1.0s (not 2.0s or 0.5s)
    task_ids = []
    for _ in range(4):
        tid = await kernel.submit_task(agent, tenant, "slow", {"delay": 0.5})
        task_ids.append(tid)

    # Wait for all
    completed = 0
    while completed < 4:
        await asyncio.sleep(0.1)
        completed = 0
        for tid in task_ids:
            t = await kernel.get_task(tid)
            if t.status == TaskStatus.COMPLETED: completed += 1
            if time.time() - start_time > 3: break # Safety break

    duration = time.time() - start_time
    assert 0.9 <= duration <= 1.5 # Allow some overhead, but verify batching
    assert completed == 4

@pytest.mark.asyncio
async def test_multi_tenant_isolation_stress(stress_system):
    kernel, _ = stress_system
    
    # Two tenants with different limits
    t1 = Tenant(tenant_id="T1", name="T1", max_concurrent_tasks=1)
    t2 = Tenant(tenant_id="T2", name="T2", max_concurrent_tasks=10)
    
    a1 = Agent(agent_id="A1", tenant_id="T1", name="A1")
    a2 = Agent(agent_id="A2", tenant_id="T2", name="A2")
    
    system_registry.register_tenant(t1)
    system_registry.register_tenant(t2)
    system_registry.register_agent(a1)
    system_registry.register_agent(a2)

    # Submit many tasks for T2 (high limit) and 1 for T1 (low limit)
    # T2 tasks should not block T1 task completion
    
    t2_task_ids = [await kernel.submit_task(a2, t2, "slow", {"delay": 0.5}) for _ in range(5)]
    t1_task_id = await kernel.submit_task(a1, t1, "slow", {"delay": 0.1})

    # Wait for T1 task
    for _ in range(20):
        await asyncio.sleep(0.1)
        t1_task = await kernel.get_task(t1_task_id)
        if t1_task.status == TaskStatus.COMPLETED: break

    assert t1_task.status == TaskStatus.COMPLETED
    # T2 tasks might still be running or just finished, but T1 should be independent
