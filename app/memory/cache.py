import valkey
import os
import json
from typing import Any, Optional

class ValkeyCache:
    def __init__(self):
        self.client = valkey.from_url(os.getenv("VALKEY_URL", "redis://localhost:6379/0"))

    async def get_session_state(self, agent_id: str) -> Optional[dict]:
        state = self.client.get(f"agent:{agent_id}:state")
        return json.loads(state) if state else None

    async def set_session_state(self, agent_id: str, state: dict, ex: int = 3600):
        self.client.set(f"agent:{agent_id}:state", json.dumps(state), ex=ex)

    async def increment_rate_limit(self, tenant_id: str) -> int:
        key = f"tenant:{tenant_id}:rate_limit"
        return self.client.incr(key)

cache = ValkeyCache()
