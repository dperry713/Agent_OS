from celery import Celery
import os
from opentelemetry.instrumentation.celery import CeleryInstrumentor

# Initialize Celery
app = Celery(
    "agent_os",
    broker=os.getenv("RABBITMQ_URL", "pyamqp://guest@localhost//"),
    backend=os.getenv("DATABASE_URL", "db+postgresql://postgres:postgres@localhost:5432/agent_os"),
    include=["app.kernel.tasks"]
)

# Optional configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1
)

# Instrument Celery with OpenTelemetry
CeleryInstrumentor().instrument()
