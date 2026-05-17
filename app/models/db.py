from sqlalchemy import Column, String, Integer, JSON, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = String # Fallback for mock if pgvector missing

Base = declarative_base()

class DBTenant(Base):
    __tablename__ = 'tenants'
    tenant_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    max_agents = Column(Integer, default=10)
    max_concurrent_tasks = Column(Integer, default=5)
    blocked_tools = Column(JSON, default=[])
    custom_routing_key = Column(String, nullable=True) # BYOC Routing

class DBAgent(Base):
    __tablename__ = 'agents'
    agent_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey('tenants.tenant_id'), nullable=False)
    name = Column(String, nullable=False)
    metadata_json = Column(JSON, default={})

class DBTask(Base):
    __tablename__ = 'tasks'
    task_id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey('agents.agent_id'), nullable=False)
    tenant_id = Column(String, ForeignKey('tenants.tenant_id'), nullable=False)
    tool_name = Column(String, nullable=False)
    input_data = Column(JSON, nullable=False)
    status = Column(String, default="queued")
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

class DBMemory(Base):
    __tablename__ = 'memory'
    tenant_id = Column(String, ForeignKey('tenants.tenant_id'), primary_key=True)
    agent_id = Column(String, ForeignKey('agents.agent_id'), primary_key=True)
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)

class DBVectorMemory(Base):
    __tablename__ = 'vector_memory'
    memory_id = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey('tenants.tenant_id'), nullable=False)
    agent_id = Column(String, ForeignKey('agents.agent_id'), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
