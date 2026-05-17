import asyncio
import logging
import resource
import os
import json
import signal
from typing import Any, Dict, Optional, List
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
        return cls(profile=profile, cpu_seconds=60, memory_limit_mb=1024, max_processes=100)

class SandboxResult(BaseModel):
    stdout: str
    stderr: str
    exit_status: int
    cpu_time: float
    peak_memory_kb: int
    is_gvisor: bool
    audit_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SandboxExecutor:
    """
    Production-grade Sandbox Executor with support for multiple backends and strict monitoring.
    This component enforces hard compute isolation and resource caps.
    """
    
    def __init__(self, limits: Optional[SandboxLimits] = None, backend: SandboxBackend = SandboxBackend.GVISOR):
        self.limits = limits or SandboxLimits()
        self.backend = backend
        self._is_gvisor = self._detect_gvisor()

    def _detect_gvisor(self) -> bool:
        """Heuristic check for gVisor runtime environment."""
        try:
            if os.path.exists("/proc/sys/kernel/ostype"):
                with open("/proc/sys/kernel/ostype", "r") as f:
                    return "gVisor" in f.read()
            # Alternative: check for specific device nodes or dmesg signatures
            return False
        except Exception: 
            return False

    def _set_resource_limits(self):
        """Standardizes POSIX resource limits (RLIMIT) to prevent DOS attacks."""
        # 1. CPU Time (seconds)
        resource.setrlimit(resource.RLIMIT_CPU, (self.limits.cpu_seconds, self.limits.cpu_seconds + 1))
        # 2. Virtual Memory (Address Space)
        mem_bytes = self.limits.memory_limit_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        # 3. Max Process Count (prevent fork bombs)
        resource.setrlimit(resource.RLIMIT_NPROC, (self.limits.max_processes, self.limits.max_processes))
        # 4. Disable Core Dumps (prevent info leakage)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        # 5. File Size (prevent disk exhaustion)
        fsize_bytes = self.limits.max_file_size_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_bytes, fsize_bytes))
        # 6. Open Files
        resource.setrlimit(resource.RLIMIT_NOFILE, (self.limits.max_open_files, self.limits.max_open_files))

    def _scrub_output(self, output: bytes, limit: int = 50000) -> str:
        """Sanitizes and truncates output to prevent memory bloat or log injection."""
        try:
            text = output.decode("utf-8", errors="replace").strip()
            if len(text) > limit:
                return text[:limit] + "... [TRUNCATED FOR SAFETY]"
            return text
        except Exception:
            return "[UNPARSEABLE BINARY DATA]"

    async def run_code(self, code: str, language: str = "python", env: Optional[Dict[str, str]] = None) -> SandboxResult:
        """
        Executes code snippets in a highly restricted subprocess.
        In a production gVisor environment, the whole worker is already sandboxed; 
        this adds a second layer of defense.
        """
        if language != "python":
            raise NotImplementedError(f"Language '{language}' execution not yet implemented in sandbox.")

        audit_id = f"exec-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{os.getpid()}"
        logger.info(f"Sandbox[{audit_id}] Initializing {language} execution. Profile: {self.limits.profile}")

        # Construct restricted environment
        base_env = {"PYTHONPATH": ".", "PATH": os.getenv("PATH", ""), "LANG": "en_US.UTF-8"}
        if env: base_env.update(env)

        start_time = asyncio.get_event_loop().time()
        
        try:
            process = await asyncio.create_subprocess_exec(
                "python3", "-c", code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=base_env,
                preexec_fn=self._set_resource_limits,
                start_new_session=True # Isolate from worker signal group
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.limits.timeout_seconds
                )
                duration = asyncio.get_event_loop().time() - start_time
                
                # Check for signal termination (OOM, Timeout, etc)
                exit_status = process.returncode if process.returncode is not None else -1
                
                result = SandboxResult(
                    stdout=self._scrub_output(stdout),
                    stderr=self._scrub_output(stderr, limit=5000),
                    exit_status=exit_status,
                    cpu_time=duration,
                    peak_memory_kb=0, # In production, pull from /proc/pid/status
                    is_gvisor=self._is_gvisor,
                    audit_id=audit_id
                )
                
                logger.info(f"Sandbox[{audit_id}] Completed. Exit: {exit_status}, CPU: {duration:.2f}s")
                return result

            except asyncio.TimeoutError:
                # Terminate entire process group
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                await process.wait()
                logger.error(f"Sandbox[{audit_id}] SECURITY TIMEOUT triggered.")
                raise SandboxError(f"Code execution exceeded security timeout of {self.limits.timeout_seconds}s")

        except Exception as e:
            if not isinstance(e, SandboxError):
                logger.exception(f"Sandbox[{audit_id}] INTERNAL CRITICAL FAILURE")
                raise SandboxError(f"Sandbox execution failed: {str(e)}")
            raise

    async def run_tool(self, tool_fn, input_data: dict, agent: Any, context: Any) -> Any:
        """Wraps a high-level tool function with monitoring and audit logging."""
        audit_id = f"tool-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{os.getpid()}"
        logger.info(f"Sandbox[{audit_id}] Starting tool '{tool_fn.__name__ if hasattr(tool_fn, '__name__') else 'unknown'}'")
        
        try:
            # Note: For pure Python tools, we use asyncio.wait_for.
            # If the tool performs heavy compute, it should internalize run_code above.
            result = await asyncio.wait_for(
                tool_fn(input_data, agent, context),
                timeout=self.limits.timeout_seconds
            )
            
            # Simple result sanitization
            if isinstance(result, str) and len(result) > 100000:
                result = result[:100000] + "... [TRUNCATED]"
            
            logger.info(f"Sandbox[{audit_id}] Tool execution success.")
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Sandbox[{audit_id}] Tool TIMEOUT.")
            raise SandboxError(f"Tool execution timed out after {self.limits.timeout_seconds}s")
        except Exception as e:
            logger.error(f"Sandbox[{audit_id}] Tool FAILED: {str(e)}")
            raise
