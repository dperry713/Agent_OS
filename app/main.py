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

from app.core.exceptions import AgentOSException, PolicyViolation, SandboxError, ToolExecutionError
from app.core.logging import setup_logging, get_logger

logger = get_logger(__name__)

# ... (rest of imports unchanged)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialization
    setup_logging()
    logger.info("starting_agent_os", version=settings.VERSION)
    yield
    # Cleanup
    logger.info("shutting_down_agent_os")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# Middleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next):
    """
    Extracts tenant_id and request_id for correlation across services.
    """
    tenant_id = request.headers.get("X-Tenant-ID")
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    request.state.tenant_id = tenant_id
    request.state.request_id = request_id
    
    # Enrich OTel Span
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("tenant_id", tenant_id or "anonymous")
        span.set_attribute("request_id", request_id)

    # Bind request context to structlog
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        tenant_id=tenant_id,
        request_id=request_id,
        path=request.url.path
    )

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.exception_handler(AgentOSException)
async def agent_os_exception_handler(request: Request, exc: AgentOSException):
    # Log internal details but return clean message
    logger.error("agent_os_error", 
                 path=request.url.path, 
                 error_type=exc.__class__.__name__, 
                 message=str(exc), 
                 details=exc.details)
    
    status_code = 400
    if isinstance(exc, PolicyViolation): status_code = 403
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "request_id": request.headers.get("X-Request-ID")
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred. Please contact support.",
            "request_id": request.headers.get("X-Request-ID")
        },
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

import valkey.asyncio as valkey_async
from app.models.db import DBTask
from sqlalchemy import select, update

# ... (rest of imports unchanged)

@app.post("/tasks/{task_id}/approve")
async def approve_task(task_id: str):
    """
    Approves a task that is AWAITING_INPUT.
    Updates the checkpoint to 'approved' and re-queues the execution.
    """
    async with await get_db_session() as session:
        result = await session.execute(select(DBTask).filter_by(task_id=task_id))
        db_task = result.scalar_one_or_none()
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # 1. Load and Update Checkpoint
        # We need tenant context for this
        async with await get_db_session(db_task.tenant_id) as tenant_session:
            from app.memory.store import MemoryStore
            from app.agents.base import AgentState
            store = MemoryStore()
            checkpoint_json = await store.get(db_task.tenant_id, db_task.agent_id, f"checkpoint:{task_id}")
            if not checkpoint_json:
                raise HTTPException(status_code=400, detail="No checkpoint found for task")
            
            state = AgentState.model_validate_json(checkpoint_json)
            state.metadata["hitl_status"] = "approved"
            await store.set(db_task.tenant_id, db_task.agent_id, f"checkpoint:{task_id}", state.model_dump_json())

        # 2. Re-queue Celery Task
        execute_agent_task.apply_async(
            args=[task_id, db_task.tenant_id, db_task.agent_id, db_task.tool_name, db_task.input_data]
        )
        
        return {"status": "resumed", "task_id": task_id}

from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

# ... (rest of imports unchanged)

@app.get("/tasks/{task_id}/events")
async def stream_task_events_sse(request: Request, task_id: str):
    """
    SSE Fallback for real-time task streaming.
    More reliable over high-latency networks or through restrictive proxies.
    """
    async def event_generator():
        client = valkey_async.from_url(settings.VALKEY_URL)
        pubsub = client.pubsub()
        await pubsub.subscribe(f"task_stream:{task_id}")
        
        try:
            async for message in pubsub.listen():
                if await request.is_disconnected():
                    break
                if message["type"] == "message":
                    yield {
                        "event": "message",
                        "data": message["data"].decode("utf-8")
                    }
        finally:
            await pubsub.unsubscribe(f"task_stream:{task_id}")
            await client.close()

    return EventSourceResponse(event_generator())

@app.websocket("/tasks/{task_id}/stream")
async def stream_task(websocket: WebSocket, task_id: str):
    await websocket.accept()
    logger.info("websocket_connected", task_id=task_id)
    
    # Heartbeat configuration
    HEARTBEAT_INTERVAL = 30
    
    async def heartbeat(ws: WebSocket):
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await ws.send_json({"type": "ping", "ts": time.time()})
        except Exception:
            pass

    client = valkey_async.from_url(settings.VALKEY_URL)
    pubsub = client.pubsub()
    
    try:
        await pubsub.subscribe(f"task_stream:{task_id}")
        
        # Start heartbeat in background
        heartbeat_task = asyncio.create_task(heartbeat(websocket))
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"].decode("utf-8"))
                
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", task_id=task_id)
    except Exception as e:
        logger.error("websocket_error", task_id=task_id, error=str(e))
    finally:
        heartbeat_task.cancel()
        await pubsub.unsubscribe(f"task_stream:{task_id}")
        await client.close()
        try:
            await websocket.close()
        except Exception:
            pass

FastAPIInstrumentor().instrument_app(app)
