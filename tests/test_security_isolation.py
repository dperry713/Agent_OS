import pytest
import asyncio
import os
import signal
from unittest.mock import MagicMock, patch
from app.runtime.sandbox import SandboxExecutor, SandboxLimits
from app.security.vault import VaultService
from app.core.config import settings
from app.core.exceptions import SandboxError

@pytest.mark.asyncio
async def test_sandbox_ulimits_cpu():
    """Verifies that CPU-heavy tasks are restricted by ulimits."""
    executor = SandboxExecutor(limits=SandboxLimits(cpu_seconds=1, timeout_seconds=5))
    # Python code that infinite loops to consume CPU
    code = "while True: pass"
    
    with pytest.raises(SandboxError) as exc:
        await executor.run_python(code, "test-tenant")
    assert "timed out" in str(exc.value)

@pytest.mark.asyncio
async def test_sandbox_fork_bomb():
    """Verifies that fork bombs are prevented by RLIMIT_NPROC."""
    executor = SandboxExecutor(limits=SandboxLimits(max_processes=2, timeout_seconds=5))
    # Attempt to fork many processes
    code = "import os; [os.fork() for _ in range(10)]"
    
    result = await executor.run_python(code, "test-tenant")
    # Should fail with exit status or stderr containing OSError
    assert result["exit_status"] != 0 or "OSError" in result["stderr"] or "BlockingIOError" in result["stderr"]

@pytest.mark.asyncio
async def test_vault_approle_flow():
    """Verifies Vault AppRole authentication logic and caching."""
    with patch("hvac.Client") as mock_hvac:
        mock_client = mock_hvac.return_value
        mock_client.auth.approle.login.return_value = {
            "auth": {
                "client_token": "test-token",
                "lease_duration": 3600
            }
        }
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"openai": "sk-test"}}
        }
        
        with patch.object(settings, "VAULT_ROLE_ID", "role-id"), \
             patch.object(settings, "VAULT_SECRET_ID", "secret-id"):
            
            vault = VaultService()
            # First call: should authenticate
            key = vault.get_llm_api_key("tenant-1", "openai")
            assert key == "sk-test"
            assert mock_client.auth.approle.login.called
            
            # Second call: should use cache
            mock_client.auth.approle.login.reset_mock()
            key2 = vault.get_llm_api_key("tenant-1", "openai")
            assert key2 == "sk-test"
            assert not mock_client.auth.approle.login.called

@pytest.mark.asyncio
async def test_rls_session_isolation():
    """Verifies that DB sessions correctly set the transaction-local tenant context."""
    from app.core.db import get_db_session
    from sqlalchemy import text
    
    tenant_id = "tenant-secure-123"
    async with await get_db_session(tenant_id) as session:
        # Check the session variable value
        res = await session.execute(text("SELECT current_setting('app.current_tenant', true)"))
        val = res.scalar()
        assert val == tenant_id
        
    # Verify that a session without tenant_id has no context
    async with await get_db_session() as session:
        res = await session.execute(text("SELECT current_setting('app.current_tenant', true)"))
        val = res.scalar()
        assert val == "" or val is None
