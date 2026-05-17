import asyncio
import logging
from celery import Celery
from opentelemetry import trace
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from app.core.config import settings

from kombu import Exchange, Queue

# Setup Celery
app = Celery(
    "agent_os",
    broker=settings.RABBITMQ_URL,
    backend=settings.DATABASE_URL.replace("postgresql+asyncpg", "db+postgresql"),
    include=["app.kernel.tasks"]
)

# Define Exchanges & Queues
default_exchange = Exchange('agentos', type='direct')
dlq_exchange = Exchange('agentos_dlq', type='direct')

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Reliability
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    
    # Queues & Routing
    task_default_queue="celery",
    task_queues=(
        Queue('celery', default_exchange, routing_key='celery',
              queue_arguments={'x-dead-letter-exchange': 'agentos_dlq',
                               'x-dead-letter-routing-key': 'dead_letter'}),
        Queue('dead_letter', dlq_exchange, routing_key='dead_letter'),
        Queue('high_priority', default_exchange, routing_key='high_priority'),
    ),
    
    # Timeouts
    task_time_limit=300, # 5 minutes hard limit
    task_soft_time_limit=240, # 4 minutes soft limit
)

# OpenTelemetry Instrumentation
CeleryInstrumentor().instrument()

logger = logging.getLogger(__name__)

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Add periodic cleanup tasks if needed
    pass
