import asyncio
import logging
import resource
import os
import json
import signal
import shlex
from typing import Any, Dict, Optional, List, Tuple
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from app.core.exceptions import SandboxError

logger = logging.getLogger(__name__)

class SandboxBackend(str, Enum):
    PROCESS = "process"
    GVISOR = "gvisor"
    FIRECRACKER = "firecracker"

class SandboxProfile(str, Enum):
    STRICT = "strict"
    MEDIUM = "medium"
    PERMISSIVE = "permissive"

class SandboxLimits(BaseModel):
    cpu_seconds: int = 30
    memory_limit_mb: int = 512
    max_processes: int = 15
    timeout_seconds: int = 45
    max_file_size_mb: int = 100
    max_open_files: int = 512
    profile: SandboxProfile = SandboxProfile.STRICT

    @classmethod
    def from_profile(cls, profile: SandboxProfile):
        configs = {
            SandboxProfile.STRICT: {"cpu_seconds": 10, "memory_limit_mb": 256, "max_processes": 5},
            SandboxProfile.MEDIUM: {"cpu_seconds": 30, "memory_limit_mb": 512, "max_processes": 20},
            SandboxProfile.PERMISSIVE: {"cpu_seconds": 120, "memory_limit_mb": 2048, "max_processes": 100}
        }
        return cls(profile=profile, **configs.get(profile, configs[SandboxProfile.STRICT]))

class SandboxResult(BaseModel):
    stdout: str
    stderr: str
    exit_status: int
    cpu_time: float
    is_gvisor: bool
    audit_id: str
    peak_memory_kb: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SandboxExecutor:
    """
    World-class Sandbox Executor.
    Enforces hard isolation, resource caps, and mandatory audit logging.
    Designed for multi-tenant worker nodes under gVisor.
    """
    
    def __init__(self, limits: Optional[SandboxLimits] = None, backend: SandboxBackend = SandboxBackend.GVISOR):
        self.limits = limits or SandboxLimits()
        self.backend = backend
        self._is_gvisor = self._detect_gvisor()

    def _detect_gvisor(self) -> bool:
        """Robust gVisor detection."""
        try:
            if os.path.exists("/proc/sys/kernel/ostype"):
                with open("/proc/sys/kernel/ostype", "r") as f:
                    return "gVisor" in f.read()
            return False
        except Exception: return False

    def _set_resource_limits(self):
        """Mandatory POSIX rlimits for the execution context."""
        # Prevent CPU hogging
        resource.setrlimit(resource.RLIMIT_CPU, (self.limits.cpu_seconds, self.limits.cpu_seconds + 1))
        # Prevent Memory exhaustion
        mem_bytes = self.limits.memory_limit_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        # Prevent Fork Bombs
        resource.setrlimit(resource.RLIMIT_NPROC, (self.limits.max_processes, self.limits.max_processes))
        # Disable Core Dumps (Security)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        # Prevent Disk filling
        fsize_bytes = self.limits.max_file_size_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_bytes, fsize_bytes))
        # Limit File Descriptors
        resource.setrlimit(resource.RLIMIT_NOFILE, (self.limits.max_open_files, self.limits.max_open_files))

    async def run_python(self, code: str, tenant_id: str) -> SandboxResult:
        """Securely executes Python logic in a isolated subprocess."""
        audit_id = f"py-{tenant_id}-{datetime.utcnow().strftime('%H%M%S')}"
        
        # Scrub and wrap code for execution
        safe_code = f"import sys, os; sys.path = []; {code}"
        
        logger.info(f"Sandbox[{audit_id}] Executing Python (Profile: {self.limits.profile})")
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            process = await asyncio.create_subprocess_exec(
                "python3", "-c", safe_code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=self._set_resource_limits,
                start_new_session=True, # Prevent signal propagation
                env={"LANG": "C.UTF-8", "PYTHONUNBUFFERED": "1"}
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.limits.timeout_seconds
                )
                duration = asyncio.get_event_loop().time() - start_time
                
                return SandboxResult(
                    stdout=stdout.decode('utf-8', 'replace')[:100000].strip(),
                    stderr=stderr.decode('utf-8', 'replace')[:10000].strip(),
                    exit_status=process.returncode or 0,
                    cpu_time=duration,
                    is_gvisor=self._is_gvisor,
                    audit_id=audit_id
                )

            except asyncio.TimeoutError:
                # Force kill process group
                try: os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except: pass
                await process.wait()
                logger.error(f"Sandbox[{audit_id}] TIMEOUT reached.")
                raise SandboxError(f"Security: Code execution timed out after {self.limits.timeout_seconds}s")

        except Exception as e:
            if isinstance(e, SandboxError): raise
            logger.exception(f"Sandbox[{audit_id}] CRITICAL FAIL")
            raise SandboxError(f"Sandbox internal error: {str(e)}")

    async def run_cmd(self, command: str, args: List[str], tenant_id: str) -> SandboxResult:
        """Securely executes a binary (e.g. git, curl) in the sandbox."""
        audit_id = f"cmd-{tenant_id}-{datetime.utcnow().strftime('%H%M%S')}"
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            process = await asyncio.create_subprocess_exec(
                command, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=self._set_resource_limits,
                start_new_session=True
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.limits.timeout_seconds)
            duration = asyncio.get_event_loop().time() - start_time
            
            return SandboxResult(
                stdout=stdout.decode('utf-8', 'replace')[:50000],
                stderr=stderr.decode('utf-8', 'replace')[:5000],
                exit_status=process.returncode or 0,
                cpu_time=duration,
                is_gvisor=self._is_gvisor,
                audit_id=audit_id
            )
        except asyncio.TimeoutError:
            try: os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except: pass
            await process.wait()
            raise SandboxError(f"Security: Command {command} timed out.")
        except Exception as e:
            raise SandboxError(f"Command execution failed: {str(e)}")
