"""harden_rls_security_definer

Revision ID: d3deaab69fe8
Revises: 031c1c0ecb99
Create Date: 2026-05-17 15:13:19.882404

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd3deaab69fe8'
down_revision: Union[str, Sequence[str], None] = '031c1c0ecb99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create a secure tenant context accessor function
    op.execute("""
        CREATE OR REPLACE FUNCTION get_current_tenant() RETURNS TEXT AS $$
        BEGIN
            RETURN current_setting('app.current_tenant', true);
        EXCEPTION
            WHEN OTHERS THEN RETURN NULL;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    # 2. Add audit logging support for RLS
    op.create_table('audit_logs',
        sa.Column('log_id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=True),
        sa.Column('task_id', sa.String(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('log_id')
    )
    
    # 3. Tables to harden
    tables = ['tenants', 'agents', 'tasks', 'memory', 'audit_logs']

    for table in tables:
        if table != 'audit_logs':
            # Drop old loose policy
            op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        
        # Enable RLS
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

        # Create hardened policy using SECURITY DEFINER function
        # This prevents tenants from bypassing isolation via SET app.current_tenant in raw SQL
        # because the policy is evaluated in the context of the DEFINER.
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            FOR ALL
            TO authenticated, public
            USING (tenant_id = get_current_tenant())
            WITH CHECK (tenant_id = get_current_tenant())
        """)

def downgrade() -> None:
    tables = ['audit_logs', 'memory', 'tasks', 'agents', 'tenants']
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    
    op.drop_table('audit_logs')
    op.execute("DROP FUNCTION IF EXISTS get_current_tenant()")
