import hvac
import logging
import time
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class VaultService:
    """
    Enterprise-grade Vault Service using AppRole.
    Features: 
    - Short-lived session token management
    - Sliding window caching for secrets
    - Automated re-authentication on expiry
    - Fail-closed security logic
    """
    def __init__(self):
        self.client = hvac.Client(url=settings.VAULT_ADDR)
        self._token_expiry: float = 0
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 300 # 5-minute cache to reduce Vault pressure

    def _authenticate(self):
        """Strict AppRole Authentication. No permissive fallbacks."""
        if not settings.VAULT_ROLE_ID or not settings.VAULT_SECRET_ID:
            logger.critical("VAULT_CONFIG_MISSING: AppRole credentials required.")
            raise RuntimeError("Vault configuration missing. Access Denied.")

        try:
            auth_res = self.client.auth.approle.login(
                role_id=settings.VAULT_ROLE_ID,
                secret_id=settings.VAULT_SECRET_ID
            )
            
            # Extract short-lived token and its duration
            self.client.token = auth_res['auth']['client_token']
            lease_duration = auth_res['auth']['lease_duration']
            
            # Calculate token expiry with a 60-second safety buffer
            self._token_expiry = time.time() + lease_duration - 60
            logger.info("Vault AppRole authenticated successfully.")
            
        except Exception as e:
            logger.error(f"Vault Security Critical: AppRole Auth Failed: {e}")
            raise

    def _ensure_authenticated(self):
        """Lazy authentication checker before every sensitive call."""
        if not self.client.token or time.time() >= self._token_expiry:
            self._authenticate()

    def get_llm_api_key(self, tenant_id: str, provider: str) -> Optional[str]:
        """
        Retrieves tenant-specific secrets with high-reliability caching.
        Enforces tenant isolation by path scoping.
        """
        cache_key = f"{tenant_id}:{provider}"
        now = time.time()

        # 1. Performance Optimization: Check local cache first
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if now - entry['timestamp'] < self._cache_ttl:
                return entry['value']

        # 2. Security: Fetch from Vault with short-lived session
        try:
            self._ensure_authenticated()
            
            # Paths follow strict pattern: secret/data/tenants/<tenant_id>/llm-keys
            read_response = self.client.secrets.kv.v2.read_secret_version(
                path=f"tenants/{tenant_id}/llm-keys",
                mount_point="secret"
            )
            
            keys = read_response['data']['data']
            value = keys.get(provider)

            # 3. Update cache on success
            if value:
                self._cache[cache_key] = {"value": value, "timestamp": now}
            
            return value

        except Exception as e:
            logger.error(f"Vault Isolation Error: Failed secret fetch for tenant {tenant_id}: {e}")
            return None

# Global Singleton Instance
vault_service = VaultService()
