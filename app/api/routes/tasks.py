from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskResponse
from app.api.dependencies import get_tenant_id
from app.worker.tasks import execute_agent_task

router = APIRouter()

@router.post("/", response_model=TaskResponse)
def create_task(task: TaskCreate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    db_task = Task(agent_id=task.agent_id, payload=task.payload, tenant_id=tenant_id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Trigger Celery Worker
    execute_agent_task.delay(db_task.id)
    
    return db_task

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.tenant_id == tenant_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task