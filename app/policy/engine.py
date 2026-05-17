import httpx
import logging
from typing import List, Optional, Any
from app.models.schemas import Tenant, Agent, AuditLogEntry
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class PolicyEngine:
    """
    Advanced Policy Engine with OPA (Open Policy Agent) support.
    Enforces fine-grained tool execution policies and tenant-level guardrails.
    """
    
    def __init__(self):
        self.opa_url = getattr(settings, "OPA_URL", None)
        self.timeout = 2.0

    async def validate_execution(self, tenant: Tenant, agent: Agent, tool_name: str) -> bool:
        """
        Validates execution by querying OPA or falling back to local RBAC.
        """
        if self.opa_url:
            return await self._query_opa(tenant, agent, tool_name)
        
        # Local Fallback (RBAC/Blocklist)
        return await self._validate_local(tenant, agent, tool_name)

    async def _query_opa(self, tenant: Tenant, agent: Agent, tool_name: str) -> bool:
        """Consults Open Policy Agent sidecar for authorization."""
        input_data = {
            "input": {
                "tenant": tenant.model_dump(),
                "agent": agent.model_dump(),
                "tool": tool_name,
                "action": "execute"
            }
        }
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(f"{self.opa_url}/v1/data/agent_os/allow", json=input_data, timeout=self.timeout)
                if r.status_code == 200:
                    return r.json().get("result", False)
                return False
        except Exception as e:
            logger.error("opa_connection_failed", error=str(e))
            return False # Fail closed for security

    async def _validate_local(self, tenant: Tenant, agent: Agent, tool_name: str) -> bool:
        """Basic local validation when OPA is unavailable."""
        if tool_name in tenant.blocked_tools:
            logger.warning("policy_violation_blocked_tool", tenant_id=tenant.tenant_id, tool=tool_name)
            return False
        
        # Additional local rules (e.g., max tools per agent) can be added here
        return True
