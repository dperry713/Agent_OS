from sqlalchemy import Column, String, Integer, JSON, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from typing import Optional

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = String

Base = declarative_base()

class TenantAwareMixin:
    """Mixin to add tenant-awareness and common audit fields."""
    tenant_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

class DBTenant(Base):
    __tablename__ = 'tenants'
    tenant_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    max_agents = Column(Integer, default=10)
    max_concurrent_tasks = Column(Integer, default=5)
    blocked_tools = Column(JSON, default=[])
    custom_routing_key = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DBAgent(Base, TenantAwareMixin):
    __tablename__ = 'agents'
    agent_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    metadata_json = Column(JSON, default={})

class DBTask(Base, TenantAwareMixin):
    __tablename__ = 'tasks'
    task_id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey('agents.agent_id'), nullable=False)
    tool_name = Column(String, nullable=False)
    input_data = Column(JSON, nullable=False)
    status = Column(String, default="queued", index=True)
    version = Column(Integer, default=1, nullable=False) # Optimistic Locking
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

class DBMemory(Base, TenantAwareMixin):
    __tablename__ = 'memory'
    agent_id = Column(String, ForeignKey('agents.agent_id'), primary_key=True)
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)

class DBVectorMemory(Base, TenantAwareMixin):
    __tablename__ = 'vector_memory'
    memory_id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey('agents.agent_id'), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)

class DBAuditLog(Base, TenantAwareMixin):
    __tablename__ = 'audit_logs'
    log_id = Column(String, primary_key=True)
    agent_id = Column(String, nullable=True)
    task_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    details = Column(JSON, nullable=True)

class DBUsageMetric(Base, TenantAwareMixin):
    __tablename__ = 'usage_metrics'
    metric_id = Column(String, primary_key=True)
    agent_id = Column(String, nullable=False)
    task_id = Column(String, nullable=False)
    tokens_used = Column(Integer, default=0)
    cost = Column(Integer, default=0) # In milli-cents

class DBSemanticCache(Base):
    __tablename__ = 'semantic_cache'
    cache_id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    query_embedding = Column(Vector(1536), nullable=False)
    result_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
