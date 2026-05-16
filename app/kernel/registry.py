from typing import Dict, Optional
from app.models.schemas import Tenant, Agent

class SystemRegistry:
    def __init__(self):
        self.tenants: Dict[str, Tenant] = {}
        self.agents: Dict[str, Agent] = {}

    def register_tenant(self, tenant: Tenant):
        self.tenants[tenant.tenant_id] = tenant

    def register_agent(self, agent: Agent):
        self.agents[agent.agent_id] = agent

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self.tenants.get(tenant_id)

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self.agents.get(agent_id)

# Global registry instance
system_registry = SystemRegistry()
