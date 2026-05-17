import hvac
import os
import time
import logging
from app.core.config import settings
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class VaultService:
    def __init__(self):
        self.client = hvac.Client(url=settings.VAULT_ADDR)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 300 # 5 minutes
        self._authenticate()

    def _authenticate(self):
        """Authenticates with Vault using AppRole or Token."""
        try:
            if settings.VAULT_ROLE_ID and settings.VAULT_SECRET_ID:
                logger.info("Authenticating with Vault via AppRole")
                auth_res = self.client.auth.approle.login(
                    role_id=settings.VAULT_ROLE_ID,
                    secret_id=settings.VAULT_SECRET_ID
                )
                self.client.token = auth_res['auth']['client_token']
            elif settings.VAULT_TOKEN:
                logger.warning("Using static VAULT_TOKEN (not recommended for production)")
                self.client.token = settings.VAULT_TOKEN
            else:
                logger.error("No Vault authentication method configured")
        except Exception as e:
            logger.error(f"Vault authentication failed: {e}")

    def get_llm_api_key(self, tenant_id: str, provider: str) -> Optional[str]:
        """
        Fetches the LLM API key with caching and automatic re-authentication.
        """
        cache_key = f"{tenant_id}:{provider}"
        now = time.time()

        # 1. Check Cache
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if now - entry['timestamp'] < self._cache_ttl:
                return entry['value']

        # 2. Fetch from Vault
        try:
            # Check if token is still valid, re-auth if not
            if not self.client.is_authenticated():
                self._authenticate()

            read_response = self.client.secrets.kv.v2.read_secret_version(
                path=f"tenants/{tenant_id}/llm-keys",
                mount_point="secret"
            )
            keys = read_response['data']['data']
            value = keys.get(provider)

            # 3. Update Cache
            if value:
                self._cache[cache_key] = {
                    'value': value,
                    'timestamp': now
                }
            return value

        except Exception as e:
            logger.error(f"Error fetching secret for tenant {tenant_id}: {e}")
            return None

vault_service = VaultService()
