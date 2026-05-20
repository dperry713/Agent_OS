from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentResponse
from app.api.dependencies import get_tenant_id

router = APIRouter()

@router.post("/", response_model=AgentResponse)
def create_agent(agent: AgentCreate, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    db_agent = Agent(name=agent.name, configuration=agent.configuration, tenant_id=tenant_id)
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, tenant_id: str = Depends(get_tenant_id), db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.tenant_id == tenant_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent