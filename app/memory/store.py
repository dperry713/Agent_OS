import aiosqlite
from typing import Any, Optional, Dict
from app.core.config import settings

class MemoryStore:
    def __init__(self, db_path: str = "agent_memory.db"):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self):
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            await self._db.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    tenant_id TEXT,
                    agent_id TEXT,
                    key TEXT,
                    value TEXT,
                    PRIMARY KEY (tenant_id, agent_id, key)
                )
            """)
            await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None

    async def get(self, tenant_id: str, agent_id: str, key: str) -> Optional[str]:
        if not self._db: await self.initialize()
        async with self._db.execute(
            "SELECT value FROM memory WHERE tenant_id = ? AND agent_id = ? AND key = ?",
            (tenant_id, agent_id, key)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set(self, tenant_id: str, agent_id: str, key: str, value: str):
        if not self._db: await self.initialize()
        await self._db.execute(
            "INSERT OR REPLACE INTO memory (tenant_id, agent_id, key, value) VALUES (?, ?, ?, ?)",
            (tenant_id, agent_id, key, value)
        )
        await self._db.commit()

    async def delete(self, tenant_id: str, agent_id: str, key: str):
        if not self._db: await self.initialize()
        await self._db.execute(
            "DELETE FROM memory WHERE tenant_id = ? AND agent_id = ? AND key = ?",
            (tenant_id, agent_id, key)
        )
        await self._db.commit()
