import asyncio
import logging
from celery import Celery
from opentelemetry import trace
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from app.core.config import settings

# Setup Celery
app = Celery(
    "agent_os",
    broker=settings.RABBITMQ_URL,
    backend=settings.DATABASE_URL.replace("postgresql+asyncpg", "db+postgresql"),
    include=["app.kernel.tasks"]
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_default_queue="celery",
    # Dead Letter Queue handling can be configured at RabbitMQ level or here
)

# OpenTelemetry Instrumentation
CeleryInstrumentor().instrument()

logger = logging.getLogger(__name__)

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Add periodic cleanup tasks if needed
    pass
