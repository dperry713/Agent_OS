from typing import Any, Optional
from app.memory.store import MemoryStore

class ToolContext:
    def __init__(self, tenant_id: str, agent_id: str, memory_store: MemoryStore):
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self._memory = memory_store

    async def get_memory(self, key: str) -> Optional[str]:
        return await self._memory.get(self.tenant_id, self.agent_id, key)

    async def set_memory(self, key: str, value: str):
        await self._memory.set(self.tenant_id, self.agent_id, key, value)

    async def delete_memory(self, key: str):
        await self._memory.delete(self.tenant_id, self.agent_id, key)
