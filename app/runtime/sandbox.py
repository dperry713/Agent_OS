import asyncio
import logging
import resource
import subprocess
import json
import os
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class SandboxLimits(BaseModel):
    cpu_seconds: int = 30
    memory_limit_mb: int = 512
    max_processes: int = 10
    timeout_seconds: int = 45

class SandboxResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_seconds: float
    memory_peak_kb: int
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
        """
        Detects if the current environment is running under gVisor.
        """
        try:
            # gVisor typically has a specific dmesg output or /proc/sys/kernel/hostname behavior
            # One reliable way is checking for 'gVisor' in certain kernel interfaces
            if os.path.exists("/proc/sys/kernel/ostype"):
                with open("/proc/sys/kernel/ostype", "r") as f:
                    if "gVisor" in f.read():
                        return True
            return False
        except Exception:
            return False

    def _set_resource_limits(self):
        """
        Sets POSIX resource limits for the child process.
        This is called in the preexec_fn of subprocess.
        """
        # Limit CPU time
        resource.setrlimit(resource.RLIMIT_CPU, (self.limits.cpu_seconds, self.limits.cpu_seconds))
        # Limit Address Space (Memory)
        mem_bytes = self.limits.memory_limit_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        # Limit number of processes
        resource.setrlimit(resource.RLIMIT_NPROC, (self.limits.max_processes, self.limits.max_processes))
        # Disable core dumps
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    async def run_tool(self, tool_fn, *args, **kwargs) -> Any:
        """
        Runs a Python tool function with strict monitoring.
        """
        logger.info(f"Executing tool in sandbox (gVisor={self._is_gvisor})")
        try:
            return await asyncio.wait_for(
                tool_fn(*args, **kwargs),
                timeout=self.limits.timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error(f"Sandbox execution timed out after {self.limits.timeout_seconds}s")
            raise TimeoutError("Tool execution exceeded time limits.")
        except Exception as e:
            logger.exception("Error during sandboxed tool execution")
            raise

    async def run_code(self, code: str, language: str = "python") -> SandboxResult:
        """
        Executes code snippets in a separate subprocess with RLS.
        """
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
            
            logger.info(f"Code execution finished in {duration:.2f}s (exit_code={process.returncode})")
            
            return SandboxResult(
                stdout=stdout.decode(),
                stderr=stderr.decode(),
                exit_code=process.returncode or 0,
                duration_seconds=duration,
                memory_peak_kb=0,
                is_gvisor=self._is_gvisor
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            logger.error("Code execution timed out and was killed.")
            raise TimeoutError("Code execution exceeded sandbox timeout.")
