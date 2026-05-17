import hvac
import os
import asyncio
from app.core.db import engine
from app.models.db import Base
from sqlalchemy import text

async def init_db():
    print("Initializing Database...")
    async with engine.begin() as conn:
        # In production, use: alembic upgrade head
        # For local dev/setup script:
        await conn.run_sync(Base.metadata.create_all)
        
        # Manually apply RLS policies if not done via Alembic
        for table in ['tenants', 'agents', 'tasks', 'memory']:
            await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            await conn.execute(text(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}"))
            await conn.execute(text(f"""
                CREATE POLICY {table}_tenant_isolation ON {table}
                USING (tenant_id = current_setting('app.current_tenant'))
            """))
    print("Database Initialized.")

def init_vault():
    print("Initializing OpenBao/Vault...")
    client = hvac.Client(
        url=os.getenv("VAULT_ADDR", "http://127.0.0.1:8200"),
        token=os.getenv("VAULT_TOKEN", "root")
    )
    
    if not client.is_authenticated():
        print("Vault not authenticated.")
        return

    # Enable KV engine if not enabled
    try:
        client.sys.enable_secrets_engine('kv', path='secret', version='2')
    except:
        pass

    # Create dummy secret for tenant t1
    client.secrets.kv.v2.create_or_update_secret(
        path='tenants/t1/llm-keys',
        secret=dict(google="fake-gemini-key-123"),
        mount_point='secret'
    )
    print("Vault Initialized with sample secrets.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--vault-only":
        init_vault()
    elif len(sys.argv) > 1 and sys.argv[1] == "--db-only":
        asyncio.run(init_db())
    else:
        init_vault()
        asyncio.run(init_db())
