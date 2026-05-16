from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from typing import List, Dict, Any
from app.models.schemas import Tenant, Agent, Task, TaskStatus
from app.kernel.registry import system_registry
from app.kernel.scheduler import KernelScheduler
from app.runtime.engine import RuntimeEngine
from app.policy.engine import PolicyEngine
from app.memory.store import MemoryStore
from app.core.logging import setup_logging
import uuid
from contextlib import asynccontextmanager

# Initialize Components
setup_logging()
memory_store = MemoryStore()
policy_engine = PolicyEngine()
runtime_engine = RuntimeEngine(policy_engine, memory_store)
kernel = KernelScheduler(runtime_engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await memory_store.initialize()
    await kernel.start()
    yield
    # Shutdown
    await kernel.stop()
    await memory_store.close()

app = FastAPI(title="Agent Runtime OS", lifespan=lifespan)

# --- Tenant Endpoints ---

@app.post("/tenants", response_model=Tenant)
async def create_tenant(tenant: Tenant):
    if system_registry.get_tenant(tenant.tenant_id):
        raise HTTPException(status_code=400, detail="Tenant already exists")
    system_registry.register_tenant(tenant)
    return tenant

@app.get("/tenants/{tenant_id}", response_model=Tenant)
async def get_tenant(tenant_id: str):
    tenant = system_registry.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

# --- Agent Endpoints ---

@app.post("/agents", response_model=Agent)
async def create_agent(agent: Agent):
    tenant = system_registry.get_tenant(agent.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    system_registry.register_agent(agent)
    return agent

# --- Task Endpoints ---

@app.post("/tasks/{tenant_id}/{agent_id}", response_model=Dict[str, str])
async def submit_task(
    tenant_id: str, 
    agent_id: str, 
    tool_name: str, 
    input_data: Dict[str, Any]
):
    tenant = system_registry.get_tenant(tenant_id)
    agent = system_registry.get_agent(agent_id)
    
    if not tenant or not agent:
        raise HTTPException(status_code=404, detail="Tenant or Agent not found")
    
    if agent.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Agent does not belong to tenant")

    # Submit to kernel
    task_id = await kernel.submit_task(agent, tenant, tool_name, input_data)
    
    return {"task_id": task_id}

@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    task = await kernel.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
