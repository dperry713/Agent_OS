from typing import List, Optional
from app.models.schemas import Tenant, Agent, AuditLogEntry
from app.core.logging import get_audit_logger
import json

audit_logger = get_audit_logger("policy")

class PolicyEngine:
    def __init__(self):
        self.default_deny = True

    async def validate_execution(self, tenant: Tenant, agent: Agent, tool_name: str) -> bool:
        """
        Validates if a tool can be executed based on tenant policy.
        """
        # Default Deny: Check if tool is explicitly blocked
        if tool_name in tenant.blocked_tools:
            audit_logger.warning(
                f"Policy violation: Tool '{tool_name}' is blocked for tenant '{tenant.tenant_id}'",
                extra={
                    "tenant_id": tenant.tenant_id,
                    "agent_id": agent.agent_id,
                    "tool": tool_name,
                    "status": "denied"
                }
            )
            return False

        # Additional rules can be added here (e.g., RBAC)
        
        audit_logger.info(
            f"Policy allowed: Tool '{tool_name}' for agent '{agent.agent_id}'",
            extra={
                "tenant_id": tenant.tenant_id,
                "agent_id": agent.agent_id,
                "tool": tool_name,
                "status": "allowed"
            }
        )
        return True

    def log_audit(self, entry: AuditLogEntry):
        audit_logger.info(
            f"Execution Audit: {entry.tool} - {entry.status}",
            extra=entry.dict()
        )
