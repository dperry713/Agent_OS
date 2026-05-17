from fastapi import FastAPI, HTTPException, Depends
from typing import List, Dict, Any
from app.models.schemas import Tenant, Agent, Task
from app.models.db import DBTask
from app.kernel.registry import system_registry
from app.kernel.tasks import execute_agent_task
from app.core.db import get_db_session
from app.core.logging import setup_logging
from sqlalchemy import select
import uuid
from contextlib import asynccontextmanager

# OpenTelemetry Imports
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

# Initialize Observability
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="Agent Runtime OS Enterprise", lifespan=lifespan)
FastAPIInstrumentor().instrument_app(app)

# --- Tenant Endpoints ---

@app.post("/tenants", response_model=Tenant)
async def create_tenant(tenant: Tenant):
    if await system_registry.get_tenant(tenant.tenant_id):
        raise HTTPException(status_code=400, detail="Tenant already exists")
    await system_registry.register_tenant(tenant)
    return tenant

@app.get("/tenants/{tenant_id}", response_model=Tenant)
async def get_tenant(tenant_id: str):
    tenant = await system_registry.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

# --- Agent Endpoints ---

@app.post("/agents", response_model=Agent)
async def create_agent(agent: Agent):
    tenant = await system_registry.get_tenant(agent.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    await system_registry.register_agent(agent)
    return agent

# --- Task Endpoints ---

@app.post("/tasks/{tenant_id}/{agent_id}", response_model=Dict[str, str])
async def submit_task(
    tenant_id: str, 
    agent_id: str, 
    tool_name: str, 
    input_data: Dict[str, Any]
):
    # Construct Task ID
    task_id = str(uuid.uuid4())

    # Submit to Celery
    execute_agent_task.delay(task_id, tenant_id, agent_id, tool_name, input_data)
    
    return {"task_id": task_id, "status": "queued"}

@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str, tenant_id: str):
    async with await get_db_session(tenant_id) as session:
        result = await session.execute(select(DBTask).filter_by(task_id=task_id))
        db_task = result.scalar_one_or_none()
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return Task(
            task_id=db_task.task_id,
            agent_id=db_task.agent_id,
            tenant_id=db_task.tenant_id,
            tool_name=db_task.tool_name,
            input_data=db_task.input_data,
            status=db_task.status,
            result=db_task.result,
            error=db_task.error,
            created_at=db_task.created_at,
            started_at=db_task.started_at,
            finished_at=db_task.finished_at
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
