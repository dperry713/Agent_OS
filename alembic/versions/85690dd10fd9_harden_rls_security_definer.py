"""harden_rls_security_definer

Revision ID: 85690dd10fd9
Revises: d3deaab69fe8
Create Date: 2026-05-17 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '85690dd10fd9'
down_revision = 'd3deaab69fe8'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create secure tenant context accessor
    op.execute("""
        CREATE OR REPLACE FUNCTION get_current_tenant() RETURNS TEXT AS $$
        BEGIN
            RETURN current_setting('app.current_tenant', true);
        EXCEPTION
            WHEN OTHERS THEN RETURN NULL;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    # 2. Re-apply hardened RLS to core tables
    tables = ['tenants', 'agents', 'tasks', 'memory']
    for table in tables:
        # Force RLS even for table owners (e.g. app user)
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        
        # Drop old loose policies if they exist
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        
        # Create hardened policy using the SECURITY DEFINER function
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            FOR ALL
            TO PUBLIC
            USING (tenant_id = get_current_tenant())
            WITH CHECK (tenant_id = get_current_tenant())
        """)

def downgrade():
    tables = ['memory', 'tasks', 'agents', 'tenants']
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute("DROP FUNCTION IF EXISTS get_current_tenant()")
