import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import health, tenants, agents, tasks, mcp
from app.db.session import engine
from app.models import base

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multi-Tenant Agent OS Control Plane",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(mcp.router, prefix="/mcp", tags=["mcp"])

@app.on_event("startup")
async def startup_event():
    # Initialize DB (Simple MVP version; alembic used in prod)
    base.Base.metadata.create_all(bind=engine)
    structlog.get_logger().info("Starting Agent OS Control Plane")