from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from typing import Optional

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db_session(tenant_id: Optional[str] = None) -> AsyncSession:
    """
    Returns an AsyncSession with the tenant context set for Row-Level Security.
    """
    session = AsyncSessionLocal()
    if tenant_id:
        # Set tenant context for RLS using transaction-local configuration
        # This prevents cross-tenant data leakage and SQL injection
        await session.execute(
            text("SELECT set_config('app.current_tenant', :tenant, true)"),
            {"tenant": tenant_id}
        )
    return session
