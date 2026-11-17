"""durable documents, AI quotas, and row-level security on every table

Supabase publishes the public schema through its REST API, and the publishable
key ships in the web app. Without RLS, anyone could read every table with that
key. With RLS on and no policies, those API roles get nothing, while the backend
connects as the table owner and is unaffected.

Revision ID: b4f1c7e82d10
Revises: a7d4e2b91c05
Create Date: 2026-11-06 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4f1c7e82d10'
down_revision: Union[str, None] = 'a7d4e2b91c05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LOCK_DOWN_PUBLIC_SCHEMA = """
DO $$
DECLARE
    t record;
BEGIN
    FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.tablename);
    END LOOP;
    -- These roles only exist on Supabase.
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
    END IF;
END $$;
"""


def upgrade() -> None:
    op.create_table('document_sequence',
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('prefix', sa.Text(), nullable=False),
    sa.Column('last_number', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('tenant_id', 'prefix')
    )
    op.create_table('document_file',
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('doc_type', sa.Text(), nullable=False),
    sa.Column('filename', sa.Text(), nullable=False),
    sa.Column('content', sa.LargeBinary(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('tenant_id', 'doc_type', 'filename')
    )
    op.create_table('ai_usage',
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('usage_date', sa.Date(), nullable=False),
    sa.Column('calls', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('tenant_id', 'usage_date')
    )
    op.create_index('idx_ai_usage_day', 'ai_usage', ['usage_date'], unique=False)

    if op.get_context().dialect.name == 'postgresql':
        op.execute(_LOCK_DOWN_PUBLIC_SCHEMA)


def downgrade() -> None:
    # RLS stays on: turning it off would re-expose every table.
    op.drop_index('idx_ai_usage_day', table_name='ai_usage')
    op.drop_table('ai_usage')
    op.drop_table('document_file')
    op.drop_table('document_sequence')
