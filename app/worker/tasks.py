from app.worker.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.task import Task
import time

@celery_app.task(bind=True)
def execute_agent_task(self, task_id: str):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return "Task not found"

        task.status = "running"
        db.commit()

        # Simulated sandbox execution
        time.sleep(2)

        task.status = "completed"
        task.result = {"output": "Simulated successful execution via MVP Sandbox"}
        db.commit()
        return task.result
    except Exception as e:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = "failed"
            task.result = {"error": str(e)}
            db.commit()
        raise e
    finally:
        db.close()