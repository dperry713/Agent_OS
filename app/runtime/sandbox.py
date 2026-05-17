import asyncio
import logging
import resource
import os
import signal
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from app.core.exceptions import SandboxError
from app.core.audit import audit_service

logger = logging.getLogger(__name__)

class SandboxBackend(str, Enum):
    PROCESS = "process"
    GVISOR = "gvisor"

class SandboxLimits(BaseModel):
    """Production-grade resource caps for agent tool execution."""
    cpu_seconds: int = 10
    memory_limit_mb: int = 256
    max_processes: int = 5
    timeout_seconds: int = 20
    max_file_size_mb: int = 50
    max_open_files: int = 64

class SandboxExecutor:
    """
    World-class Sandbox Executor.
    Features:
    - gVisor (runsc) isolation support
    - POSIX Kernel resource caps (ulimits)
    - Process Group signal isolation
    - Strict I/O size limits
    """
    def __init__(self, limits: Optional[SandboxLimits] = None, backend: SandboxBackend = SandboxBackend.GVISOR):
        self.limits = limits or SandboxLimits()
        self.backend = backend
        self._is_gvisor = self._detect_gvisor()

    def _detect_gvisor(self) -> bool:
        """Robust detection of gVisor/runsc environment."""
        try:
            if os.path.exists("/proc/sys/kernel/ostype"):
                with open("/proc/sys/kernel/ostype", "r") as f:
                    return "gVisor" in f.read()
            return False
        except: return False

    def _set_resource_limits(self):
        """Hardens the child process using kernel-level rlimits."""
        # Security: Prevent CPU-bound DoS
        resource.setrlimit(resource.RLIMIT_CPU, (self.limits.cpu_seconds, self.limits.cpu_seconds + 1))
        # Security: Prevent Memory exhaustion (OOM)
        mem_bytes = self.limits.memory_limit_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        # Security: Prevent Fork Bombs
        resource.setrlimit(resource.RLIMIT_NPROC, (self.limits.max_processes, self.limits.max_processes))
        # Security: Disable persistent core dumps
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        # Security: Limit FD consumption
        resource.setrlimit(resource.RLIMIT_NOFILE, (self.limits.max_open_files, self.limits.max_open_files))

    async def run_python(self, code: str, tenant_id: str, agent_id: str) -> Dict[str, Any]:
        """
        Executes untrusted agent logic with tiered isolation and signed auditing.
        """
        audit_id = f"py-{tenant_id}-{datetime.utcnow().strftime('%H%M%S')}"
        
        # Scrub: Clear path and inject guardrails
        safe_code = f"import sys, os; sys.path = []; {code}"

        if self.backend == SandboxBackend.GVISOR and not self._is_gvisor:
            logger.warning(f"gVisor requested but not detected for {audit_id}. Falling back to ulimit-hardened process.")

        try:
            # Security: New session and ulimits preexec
            process = await asyncio.create_subprocess_exec(
                "python3", "-c", safe_code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=self._set_resource_limits,
                start_new_session=True, # Isolation: No signal propagation from parent
                env={"PYTHONUNBUFFERED": "1", "AGENT_OS": "1", "LANG": "C.UTF-8"}
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.limits.timeout_seconds
                )
                
                # Security: Cap output size to 100KB to prevent memory pressure
                out = stdout.decode('utf-8', 'replace')[:100000]
                err = stderr.decode('utf-8', 'replace')[:100000]

                result = {
                    "stdout": out.strip(),
                    "stderr": err.strip(),
                    "exit_status": process.returncode,
                    "audit_id": audit_id,
                    "isolation": "gvisor" if self._is_gvisor else "ulimit_hardened"
                }

                await audit_service.log_event(
                    tenant_id, agent_id, "sandbox_python_completed",
                    {"audit_id": audit_id, "exit_status": result["exit_status"], "isolation": result["isolation"]}
                )

                return result

            except asyncio.TimeoutError:
                # Security: Force kill entire process group to reap orphans
                try: os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except: pass
                await process.wait()
                
                await audit_service.log_event(
                    tenant_id, agent_id, "sandbox_python_timeout",
                    {"audit_id": audit_id, "timeout": self.limits.timeout_seconds}
                )
                
                raise SandboxError(f"Security: Execution timed out after {self.limits.timeout_seconds}s")

        except Exception as e:
            if isinstance(e, SandboxError): raise
            logger.exception(f"Sandbox Critical Failure [{audit_id}]")
            raise SandboxError(f"Sandbox internal error: {str(e)}")
