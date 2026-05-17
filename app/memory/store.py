from sqlalchemy import text
from typing import Optional
from app.core.db import get_db_session, engine

class MemoryStore:
    def __init__(self):
        pass

    async def initialize(self):
        # Tables are created via Alembic in production.
        pass

    async def close(self):
        # Engine disposal handled at app level if needed.
        pass

    async def get(self, tenant_id: str, agent_id: str, key: str) -> Optional[str]:
        async with await get_db_session(tenant_id) as session:
            result = await session.execute(
                text("SELECT value FROM memory WHERE tenant_id = :t AND agent_id = :a AND key = :k"),
                {"t": tenant_id, "a": agent_id, "k": key}
            )
            row = result.fetchone()
            return row[0] if row else None

    async def set(self, tenant_id: str, agent_id: str, key: str, value: str):
        async with await get_db_session(tenant_id) as session:
            await session.execute(
                text("""
                    INSERT INTO memory (tenant_id, agent_id, key, value) 
                    VALUES (:t, :a, :k, :v)
                    ON CONFLICT (tenant_id, agent_id, key) DO UPDATE SET value = :v
                """),
                {"t": tenant_id, "a": agent_id, "k": key, "v": value}
            )
            await session.commit()

    async def delete(self, tenant_id: str, agent_id: str, key: str):
        async with await get_db_session(tenant_id) as session:
            await session.execute(
                text("DELETE FROM memory WHERE tenant_id = :t AND agent_id = :a AND key = :k"),
                {"t": tenant_id, "a": agent_id, "k": key}
            )
            await session.commit()
