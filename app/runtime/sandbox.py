import asyncio
import logging
import resource
import subprocess
import json
import os
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

class SandboxProfile(str, Enum):
    STRICT = "strict"
    MEDIUM = "medium"
    PERMISSIVE = "permissive"

class SandboxLimits(BaseModel):
    cpu_seconds: int = 30
    memory_limit_mb: int = 512
    max_processes: int = 10
    timeout_seconds: int = 45
    max_file_size_mb: int = 50
    max_open_files: int = 256
    profile: SandboxProfile = SandboxProfile.STRICT

    @classmethod
    def from_profile(cls, profile: SandboxProfile):
        if profile == SandboxProfile.STRICT:
            return cls(profile=profile, cpu_seconds=10, memory_limit_mb=256, max_processes=5)
        elif profile == SandboxProfile.MEDIUM:
            return cls(profile=profile, cpu_seconds=30, memory_limit_mb=512, max_processes=20)
        else:
            return cls(profile=profile, cpu_seconds=60, memory_limit_mb=1024, max_processes=100)

class SandboxResult(BaseModel):
    stdout: str
    stderr: str
    exit_status: int
    cpu_time: float
    peak_memory_kb: int
    is_gvisor: bool

class SandboxExecutor:
    """
    Executes potentially untrusted code or tools within a controlled environment.
    Designed to run inside a gVisor-sandboxed worker for layered security.
    """
    
    def __init__(self, limits: Optional[SandboxLimits] = None):
        self.limits = limits or SandboxLimits()
        self._is_gvisor = self._detect_gvisor()

    def _detect_gvisor(self) -> bool:
        """Detects if the current environment is running under gVisor."""
        try:
            if os.path.exists("/proc/sys/kernel/ostype"):
                with open("/proc/sys/kernel/ostype", "r") as f:
                    if "gVisor" in f.read():
                        return True
            return False
        except Exception:
            return False

    def _set_resource_limits(self):
        """Sets strict POSIX rlimits for the child process."""
        resource.setrlimit(resource.RLIMIT_CPU, (self.limits.cpu_seconds, self.limits.cpu_seconds))
        mem_bytes = self.limits.memory_limit_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        resource.setrlimit(resource.RLIMIT_NPROC, (self.limits.max_processes, self.limits.max_processes))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        fsize_bytes = self.limits.max_file_size_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_bytes, fsize_bytes))
        resource.setrlimit(resource.RLIMIT_NOFILE, (self.limits.max_open_files, self.limits.max_open_files))

    def _audit_log(self, context: dict, action: str, result: str):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "gvisor_active": self._is_gvisor,
            "action": action,
            "result": result,
            **context
        }
        logger.info(f"AUDIT_SANDBOX: {json.dumps(log_entry)}")

    async def run_tool(self, tool_fn, input_data: dict, agent: Any, context: Any) -> Any:
        """Runs a Python tool function with strict monitoring and audit logging."""
        audit_ctx = {"tenant_id": context.tenant_id, "agent_id": context.agent_id}
        self._audit_log(audit_ctx, "run_tool_start", "pending")
        
        try:
            result = await asyncio.wait_for(
                tool_fn(input_data, agent, context),
                timeout=self.limits.timeout_seconds
            )
            
            # I/O Sanitization: Ensure serializability and limit size
            try:
                json.dumps(result)
            except (TypeError, ValueError):
                result = str(result)
            
            if isinstance(result, str) and len(result) > 50000:
                result = result[:50000] + "... [TRUNCATED FOR SAFETY]"
                
            self._audit_log(audit_ctx, "run_tool_end", "success")
            return result
        except asyncio.TimeoutError:
            self._audit_log(audit_ctx, "run_tool_end", "timeout")
            logger.error(f"Sandbox tool execution timed out after {self.limits.timeout_seconds}s")
            raise TimeoutError("Tool execution exceeded time limits.")
        except Exception as e:
            self._audit_log(audit_ctx, "run_tool_end", f"failed: {str(e)}")
            logger.exception("Error during sandboxed tool execution")
            raise

    async def run_code(self, code: str, language: str = "python") -> SandboxResult:
        """Executes code snippets in a separate subprocess with RLS."""
        if language != "python":
            raise NotImplementedError(f"Language {language} not yet supported in sandbox.")

        start_time = asyncio.get_event_loop().time()
        
        process = await asyncio.create_subprocess_exec(
            "python3", "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=self._set_resource_limits
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.limits.timeout_seconds
            )
            duration = asyncio.get_event_loop().time() - start_time
            
            logger.info(f"Code execution finished in {duration:.2f}s (exit_status={process.returncode})")
            
            return SandboxResult(
                stdout=stdout.decode(),
                stderr=stderr.decode(),
                exit_status=process.returncode or 0,
                cpu_time=duration,
                peak_memory_kb=0, # Peak tracking would require /proc or a wrapper
                is_gvisor=self._is_gvisor
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            logger.error("Code execution timed out and was killed.")
            raise TimeoutError("Code execution exceeded sandbox timeout.")
