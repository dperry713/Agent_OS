"""initial_schema

Revision ID: 031c1c0ecb99
Revises: 
Create Date: 2026-05-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '031c1c0ecb99'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create Tables
    op.create_table('tenants',
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('max_agents', sa.Integer(), nullable=True),
        sa.Column('max_concurrent_tasks', sa.Integer(), nullable=True),
        sa.Column('blocked_tools', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('tenant_id')
    )
    op.create_table('agents',
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ),
        sa.PrimaryKeyConstraint('agent_id')
    )
    op.create_table('tasks',
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('tool_name', sa.String(), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.agent_id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ),
        sa.PrimaryKeyConstraint('task_id')
    )
    op.create_table('memory',
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.agent_id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ),
        sa.PrimaryKeyConstraint('tenant_id', 'agent_id', 'key')
    )

    # 2. Enable Row-Level Security (RLS)
    for table in ['tenants', 'agents', 'tasks', 'memory']:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.current_tenant'))
        """)

def downgrade():
    for table in ['memory', 'tasks', 'agents', 'tenants']:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    
    op.drop_table('memory')
    op.drop_table('tasks')
    op.drop_table('agents')
    op.drop_table('tenants')
