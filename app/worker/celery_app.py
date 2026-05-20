from celery import Celery
from app.core.config import settings

broker_url = settings.CELERY_BROKER_URL
result_backend = settings.CELERY_RESULT_BACKEND

if settings.USE_LOCAL_CELERY:
    # Use memory broker and result backend for no-dependency local runs
    broker_url = "memory://"
    result_backend = "cache+memory://"

celery_app = Celery(
    "worker",
    broker=broker_url,
    backend=result_backend
)

celery_app.conf.task_routes = {"app.worker.tasks.*": "main-queue"}
celery_app.conf.update(task_track_started=True)
if settings.USE_LOCAL_CELERY:
    celery_app.conf.update(task_always_eager=True)