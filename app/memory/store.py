from typing import Optional, List
from app.core.db import get_db_session
from app.models.db import DBMemory, DBVectorMemory
from sqlalchemy import select
import uuid

class MemoryStore:
    async def get(self, tenant_id: str, agent_id: str, key: str) -> Optional[str]:
        async with await get_db_session(tenant_id) as session:
            result = await session.execute(
                select(DBMemory).filter_by(agent_id=agent_id, key=key)
            )
            db_mem = result.scalar_one_or_none()
            return db_mem.value if db_mem else None

    async def set(self, tenant_id: str, agent_id: str, key: str, value: str):
        async with await get_db_session(tenant_id) as session:
            db_mem = DBMemory(tenant_id=tenant_id, agent_id=agent_id, key=key, value=value)
            await session.merge(db_mem)
            await session.commit()

    async def delete(self, tenant_id: str, agent_id: str, key: str):
        async with await get_db_session(tenant_id) as session:
            result = await session.execute(
                select(DBMemory).filter_by(agent_id=agent_id, key=key)
            )
            db_mem = result.scalar_one_or_none()
            if db_mem:
                await session.delete(db_mem)
                await session.commit()

    async def add_long_term_memory(self, tenant_id: str, agent_id: str, content: str, embedding: List[float]):
        """Inserts a semantic memory into pgvector store."""
        async with await get_db_session(tenant_id) as session:
            mem = DBVectorMemory(
                memory_id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                agent_id=agent_id,
                content=content,
                embedding=embedding
            )
            session.add(mem)
            await session.commit()

    async def search_long_term_memory(self, tenant_id: str, agent_id: str, query_embedding: List[float], limit: int = 5):
        """Performs semantic search using pgvector's L2 distance."""
        async with await get_db_session(tenant_id) as session:
            result = await session.execute(
                select(DBVectorMemory)
                .filter_by(agent_id=agent_id)
                .order_by(DBVectorMemory.embedding.l2_distance(query_embedding))
                .limit(limit)
            )
            return [m.content for m in result.scalars().all()]
