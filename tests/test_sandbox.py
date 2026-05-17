import pytest
import asyncio
from app.runtime.sandbox import SandboxExecutor, SandboxLimits, SandboxProfile
from app.core.exceptions import SandboxError

@pytest.fixture
def sandbox():
    return SandboxExecutor(limits=SandboxLimits.from_profile(SandboxProfile.STRICT))

@pytest.mark.asyncio
async def test_sandbox_python_success(sandbox):
    code = "print('hello world')"
    result = await sandbox.run_python(code, tenant_id="test_tenant")
    assert result.exit_status == 0
    assert result.stdout == "hello world"

@pytest.mark.asyncio
async def test_sandbox_cpu_timeout(sandbox):
    # Tighten limits for test
    sandbox.limits.cpu_seconds = 1
    sandbox.limits.timeout_seconds = 2
    
    code = "import time; [x**2 for x in range(10**7)]" # CPU heavy
    with pytest.raises(SandboxError) as exc:
        await sandbox.run_python(code, tenant_id="test_tenant")
    assert "timeout" in str(exc.value).lower()

@pytest.mark.asyncio
async def test_sandbox_memory_limit(sandbox):
    sandbox.limits.memory_limit_mb = 50
    # Attempt to allocate 200MB
    code = "x = ' ' * (200 * 1024 * 1024)"
    result = await sandbox.run_python(code, tenant_id="test_tenant")
    assert result.exit_status != 0 # Should fail with MemoryError/OOM

@pytest.mark.asyncio
async def test_sandbox_file_size_limit(sandbox, tmp_path):
    sandbox.limits.max_file_size_mb = 1
    code = "with open('bigfile', 'w') as f: f.write(' ' * 2*1024*1024)"
    result = await sandbox.run_python(code, tenant_id="test_tenant")
    assert result.exit_status != 0 # Should fail with SIGXFSZ or error
