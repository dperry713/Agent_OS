import pytest
import asyncio
from app.models.schemas import Tenant, Agent, TaskStatus
from app.kernel.registry import system_registry
from app.kernel.scheduler import KernelScheduler
from app.runtime.engine import RuntimeEngine
from app.policy.engine import PolicyEngine
from app.memory.store import MemoryStore

@pytest.fixture
async def setup_system():
    db_file = "test_agent_memory.db"
    memory = MemoryStore(db_file) 
    await memory.initialize()
    policy = PolicyEngine()
    runtime = RuntimeEngine(policy, memory)
    kernel = KernelScheduler(runtime)
    await kernel.start()
    yield kernel, policy, memory
    await kernel.stop()
    await memory.close()
    import os
    if os.path.exists(db_file):
        os.remove(db_file)

@pytest.mark.asyncio
async def test_task_execution(setup_system):
    kernel, policy, memory = setup_system
    
    tenant = Tenant(tenant_id="t1", name="Tenant 1")
    agent = Agent(agent_id="a1", tenant_id="t1", name="Agent 1")
    system_registry.register_tenant(tenant)
    system_registry.register_agent(agent)

    task_id = await kernel.submit_task(agent, tenant, "echo", {"message": "hello"})
    task = await kernel.get_task(task_id)
    
    # Manually trigger execution for test (since we don't have the full background loop running in isolation)
    await kernel.run_task_immediately(task, agent, tenant)
    
    result_task = await kernel.get_task(task_id)
    assert result_task.status == TaskStatus.COMPLETED
    assert result_task.result == {"output": "hello"}

@pytest.mark.asyncio
async def test_policy_denial(setup_system):
    kernel, policy, memory = setup_system
    
    tenant = Tenant(tenant_id="t2", name="Tenant 2", blocked_tools=["echo"])
    agent = Agent(agent_id="a2", tenant_id="t2", name="Agent 2")
    system_registry.register_tenant(tenant)
    system_registry.register_agent(agent)

    task_id = await kernel.submit_task(agent, tenant, "echo", {"message": "should fail"})
    task = await kernel.get_task(task_id)
    
    await kernel.run_task_immediately(task, agent, tenant)
    
    result_task = await kernel.get_task(task_id)
    assert result_task.status == TaskStatus.FAILED
    assert "Policy violation" in result_task.error

@pytest.mark.asyncio
async def test_memory_tool(setup_system):
    kernel, policy, memory = setup_system
    
    tenant = Tenant(tenant_id="t3", name="Tenant 3")
    agent = Agent(agent_id="a3", tenant_id="t3", name="Agent 3")
    system_registry.register_tenant(tenant)
    system_registry.register_agent(agent)

    # Set memory via tool
    task_id_set = await kernel.submit_task(agent, tenant, "memory", {"action": "set", "key": "foo", "value": "bar"})
    # Get memory via tool
    task_id_get = await kernel.submit_task(agent, tenant, "memory", {"action": "get", "key": "foo"})
    
    # We need to wait for the worker loop or run manually
    # Since worker loop is running in setup_system, we just poll
    
    for _ in range(10):
        await asyncio.sleep(0.1)
        task_get = await kernel.get_task(task_id_get)
        if task_get and task_get.status == TaskStatus.COMPLETED:
            break
            
    assert task_get.result == {"value": "bar"}

@pytest.mark.asyncio
async def test_memory_isolation(setup_system):
    kernel, policy, memory = setup_system
    
    await memory.set("t1", "a1", "secret", "tenant1_data")
    await memory.set("t2", "a2", "secret", "tenant2_data")
    
    val1 = await memory.get("t1", "a1", "secret")
    val2 = await memory.get("t2", "a2", "secret")
    
    assert val1 == "tenant1_data"
    assert val2 == "tenant2_data"
    
    # Cross-tenant access check
    cross_val = await memory.get("t1", "a2", "secret")
    assert cross_val is None
