from typing import Any, Dict, Optional

class AgentOSException(Exception):
    """Base exception for all Agent_OS errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}

class PolicyViolation(AgentOSException):
    """Raised when an action violates a tenant or global policy."""
    pass

class SandboxError(AgentOSException):
    """Raised when an error occurs during sandboxed execution."""
    pass

class ToolExecutionError(AgentOSException):
    """Raised when a tool fails to execute correctly."""
    pass

class SecretNotFoundError(AgentOSException):
    """Raised when a required secret is missing from OpenBao."""
    pass

class RateLimitExceeded(AgentOSException):
    """Raised when a tenant exceeds their allotted rate limits."""
    pass

class AgentLoopError(AgentOSException):
    """Raised when an error occurs within an agent reasoning loop."""
    pass
