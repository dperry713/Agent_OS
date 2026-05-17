from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import uuid
import time
import logging
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import AgentOSException
from app.models.schemas import Tenant, Agent, Task
from app.kernel.registry import system_registry
from app.kernel.tasks import execute_agent_task
from app.core.db import get_db_session

# OpenTelemetry
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialization
    setup_logging()
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    yield
    # Cleanup
    logger.info(f"Shutting down {settings.PROJECT_NAME}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# Middleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Exception Handlers
@app.exception_handler(AgentOSException)
async def agent_os_exception_handler(request: Request, exc: AgentOSException):
    return JSONResponse(
        status_code=400,
        content={"message": str(exc), "details": exc.details},
    )

from app.core.metrics import metrics

# --- Endpoints ---

@app.get("/metrics")
async def get_metrics():
    return metrics.get_latest_metrics()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}

@app.post("/tasks/{tenant_id}/{agent_id}")
async def submit_task(tenant_id: str, agent_id: str, tool_name: str, input_data: Dict[str, Any]):
    tenant = await system_registry.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    task_id = str(uuid.uuid4())
    routing_key = tenant.custom_routing_key or "celery"

    execute_agent_task.apply_async(
        args=[task_id, tenant_id, agent_id, tool_name, input_data],
        queue=routing_key
    )
    
    return {"task_id": task_id, "status": "queued"}

@app.websocket("/tasks/{task_id}/stream")
async def stream_task(websocket: WebSocket, task_id: str):
    await websocket.accept()
    # Streaming logic via Valkey PubSub...
    try:
        while True:
            data = await websocket.receive_text()
            # Handle client messages if needed
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task {task_id}")

FastAPIInstrumentor().instrument_app(app)
