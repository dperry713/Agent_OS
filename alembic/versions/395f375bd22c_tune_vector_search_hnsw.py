"""tune_vector_search_hnsw

Revision ID: 395f375bd22c
Revises: d3deaab69fe8
Create Date: 2026-05-17 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '395f375bd22c'
down_revision: Union[str, Sequence[str], None] = 'd3deaab69fe8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Enable pgvector extension if not already enabled (should be from previous steps)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Tune vector search with HNSW (Hierarchical Navigable Small World) index
    # HNSW provides much faster search performance than IVFFlat for large datasets.
    # We use cosine distance (vector_cosine_ops) which is standard for embeddings.
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_vector_memory_embedding_hnsw 
        ON vector_memory 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)
    
    # Create a table for semantic caching of tool results
    op.create_table('semantic_cache',
        sa.Column('cache_id', sa.String(), primary_key=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('query_embedding', sa.Vector(1536), nullable=False),
        sa.Column('result_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True)
    )
    
    # Add HNSW index for the semantic cache too
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_semantic_cache_embedding_hnsw 
        ON semantic_cache 
        USING hnsw (query_embedding vector_cosine_ops);
    """)
    
    # Enable RLS on semantic cache
    op.execute("ALTER TABLE semantic_cache ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY semantic_cache_tenant_isolation ON semantic_cache
        USING (tenant_id = get_current_tenant())
    """)

def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS semantic_cache_tenant_isolation ON semantic_cache")
    op.drop_table('semantic_cache')
    op.execute("DROP INDEX IF EXISTS idx_vector_memory_embedding_hnsw")
