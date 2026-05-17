import hvac
import os
from app.core.config import settings
from typing import Optional

class VaultService:
    def __init__(self):
        self.client = hvac.Client(
            url=settings.VAULT_ADDR,
            token=os.getenv("VAULT_TOKEN")
        )

    def get_llm_api_key(self, tenant_id: str, provider: str) -> Optional[str]:
        """
        Dynamically fetches the LLM API key for a specific tenant and provider from OpenBao.
        """
        try:
            read_response = self.client.secrets.kv.v2.read_secret_version(
                path=f"tenants/{tenant_id}/llm-keys",
                mount_point="secret"
            )
            keys = read_response['data']['data']
            return keys.get(provider)
        except Exception as e:
            print(f"Error fetching secret from Vault: {e}")
            return None

vault_service = VaultService()
