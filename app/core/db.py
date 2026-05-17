from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from typing import Optional

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/agent_os")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db_session(tenant_id: Optional[str] = None) -> AsyncSession:
    """
    Returns an AsyncSession with the tenant context set for Row-Level Security.
    """
    session = AsyncSessionLocal()
    if tenant_id:
        # Set tenant context for RLS
        await session.execute(text(f"SET app.current_tenant = '{tenant_id}'"))
    return session
