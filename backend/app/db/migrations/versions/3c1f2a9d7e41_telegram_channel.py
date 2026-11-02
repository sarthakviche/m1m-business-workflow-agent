"""telegram channel: identities, link codes, inbound dedup, conversation state

Revision ID: 3c1f2a9d7e41
Revises: 8be607b7d55e
Create Date: 2026-11-02 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c1f2a9d7e41'
down_revision: Union[str, None] = '8be607b7d55e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CHANNELS = "channel IN ('telegram','whatsapp')"

# SQLite reflects UUID columns as NUMERIC; batch mode would recreate the table
# with NUMERIC affinity, which can coerce digit-only UUID hex strings to numbers.
# Pin the real types so the rebuilt table matches the model.
def _convlog_uuid_columns() -> list:
    # Fresh Column objects per call: a Column can only be bound to one Table.
    return [
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('tenant_id', sa.UUID(), sa.ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False),
    ]


def upgrade() -> None:
    with op.batch_alter_table('conversation_log', reflect_args=_convlog_uuid_columns()) as batch:
        batch.add_column(sa.Column('conversation_id', sa.UUID(), nullable=True))
        batch.drop_constraint('ck_convlog_channel', type_='check')
        batch.create_check_constraint('ck_convlog_channel', "channel IN ('whatsapp','web','telegram')")
        batch.create_index('idx_convlog_conversation_time', ['conversation_id', 'created_at'])

    op.create_table('conversation_state',
    sa.Column('conversation_id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('state', sa.JSON(), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('conversation_id')
    )
    op.create_table('channel_identity',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('channel', sa.Text(), nullable=False),
    sa.Column('external_user_id', sa.Text(), nullable=False),
    sa.Column('external_chat_id', sa.Text(), nullable=False),
    sa.Column('display_name', sa.Text(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.CheckConstraint(_CHANNELS, name='ck_channel_identity_channel'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('channel', 'external_user_id', name='uq_channel_identity_user')
    )
    op.create_index('idx_channel_identity_tenant', 'channel_identity', ['tenant_id'], unique=False)
    op.create_table('channel_link_code',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('channel', sa.Text(), nullable=False),
    sa.Column('code_hash', sa.Text(), nullable=False),
    sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('used_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.CheckConstraint(_CHANNELS, name='ck_channel_link_code_channel'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code_hash', name='uq_channel_link_code_hash')
    )
    op.create_table('channel_inbound_event',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('channel', sa.Text(), nullable=False),
    sa.Column('external_event_id', sa.Text(), nullable=False),
    sa.Column('received_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.CheckConstraint(_CHANNELS, name='ck_channel_inbound_event_channel'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('channel', 'external_event_id', name='uq_channel_inbound_event')
    )


def downgrade() -> None:
    op.drop_table('channel_inbound_event')
    op.drop_table('channel_link_code')
    op.drop_index('idx_channel_identity_tenant', table_name='channel_identity')
    op.drop_table('channel_identity')
    op.drop_table('conversation_state')

    # Telegram rows would violate the narrower constraint; remove them first.
    op.execute("DELETE FROM conversation_log WHERE channel = 'telegram'")
    reflect_args = _convlog_uuid_columns() + [sa.Column('conversation_id', sa.UUID(), nullable=True)]
    with op.batch_alter_table('conversation_log', reflect_args=reflect_args) as batch:
        batch.drop_index('idx_convlog_conversation_time')
        batch.drop_constraint('ck_convlog_channel', type_='check')
        batch.create_check_constraint('ck_convlog_channel', "channel IN ('whatsapp','web')")
        batch.drop_column('conversation_id')
