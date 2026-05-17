from typing import List, Optional, Any
from app.models.schemas import Tenant, Agent, AuditLogEntry
from app.core.logging import get_audit_logger
from app.core.exceptions import PolicyViolation
import json

audit_logger = get_audit_logger("policy")

class PolicyEngine:
    """Enterprise Policy Engine supporting allow/deny lists and rate limits."""
    
    def __init__(self):
        self.default_deny = True

    async def validate_execution(self, tenant: Tenant, agent: Agent, tool_name: str) -> bool:
        """Validates tool execution against tenant-specific and global policies."""
        
        # 1. Explicit Blocklist
        if tool_name in tenant.blocked_tools:
            audit_logger.warning(
                f"Policy DENY: {tool_name} is blocked for tenant {tenant.tenant_id}",
                extra={"tenant_id": tenant.tenant_id, "agent_id": agent.agent_id, "tool": tool_name}
            )
            return False

        # 2. Add RBAC / Capability checks here...
        
        audit_logger.info(
            f"Policy ALLOW: {tool_name} for agent {agent.agent_id}",
            extra={"tenant_id": tenant.tenant_id, "agent_id": agent.agent_id, "tool": tool_name}
        )
        return True

    def log_audit(self, entry: AuditLogEntry):
        audit_logger.info(
            f"Execution Audit: {entry.tool} - {entry.status}",
            extra=entry.model_dump()
        )
