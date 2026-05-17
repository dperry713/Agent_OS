from typing import Optional
from sqlalchemy import select
from app.models.schemas import Tenant, Agent
from app.models.db import DBTenant, DBAgent
from app.core.db import get_db_session

class SystemRegistry:
    async def register_tenant(self, tenant: Tenant):
        async with await get_db_session(tenant.tenant_id) as session:
            db_tenant = DBTenant(
                tenant_id=tenant.tenant_id,
                name=tenant.name,
                max_agents=tenant.max_agents,
                max_concurrent_tasks=tenant.max_concurrent_tasks,
                blocked_tools=tenant.blocked_tools
            )
            session.add(db_tenant)
            await session.commit()

    async def register_agent(self, agent: Agent):
        async with await get_db_session(agent.tenant_id) as session:
            db_agent = DBAgent(
                agent_id=agent.agent_id,
                tenant_id=agent.tenant_id,
                name=agent.name,
                metadata_json=agent.metadata
            )
            session.add(db_agent)
            await session.commit()

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        async with await get_db_session(tenant_id) as session:
            result = await session.execute(select(DBTenant).filter_by(tenant_id=tenant_id))
            db_tenant = result.scalar_one_or_none()
            if db_tenant:
                return Tenant(
                    tenant_id=db_tenant.tenant_id,
                    name=db_tenant.name,
                    max_agents=db_tenant.max_agents,
                    max_concurrent_tasks=db_tenant.max_concurrent_tasks,
                    blocked_tools=db_tenant.blocked_tools
                )
            return None

    async def get_agent(self, tenant_id: str, agent_id: str) -> Optional[Agent]:
        async with await get_db_session(tenant_id) as session:
            result = await session.execute(select(DBAgent).filter_by(agent_id=agent_id))
            db_agent = result.scalar_one_or_none()
            if db_agent:
                return Agent(
                    agent_id=db_agent.agent_id,
                    tenant_id=db_agent.tenant_id,
                    name=db_agent.name,
                    metadata=db_agent.metadata_json
                )
            return None

system_registry = SystemRegistry()
