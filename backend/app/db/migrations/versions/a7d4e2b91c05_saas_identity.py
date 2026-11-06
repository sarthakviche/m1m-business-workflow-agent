"""saas identity: link users to the auth provider, server-side onboarding state

Revision ID: a7d4e2b91c05
Revises: 3c1f2a9d7e41
Create Date: 2026-11-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7d4e2b91c05'
down_revision: Union[str, None] = '3c1f2a9d7e41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# SQLite reflects UUID columns as NUMERIC; pin the real types when batch mode
# rebuilds the table (see the note in 3c1f2a9d7e41).
def _app_user_uuid_columns() -> list:
    return [
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('tenant_id', sa.UUID(), sa.ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False),
    ]


def upgrade() -> None:
    with op.batch_alter_table('app_user', reflect_args=_app_user_uuid_columns()) as batch:
        batch.add_column(sa.Column('auth_subject', sa.Text(), nullable=True))
        batch.add_column(sa.Column('email', sa.Text(), nullable=True))
        batch.alter_column('phone', existing_type=sa.Text(), nullable=True)
        batch.create_unique_constraint('uq_app_user_auth_subject', ['auth_subject'])

    op.add_column('tenant', sa.Column('onboarded_at', sa.TIMESTAMP(timezone=True), nullable=True))
    # Businesses that already exist have finished setup.
    op.execute("UPDATE tenant SET onboarded_at = CURRENT_TIMESTAMP")


def downgrade() -> None:
    op.drop_column('tenant', 'onboarded_at')
    # Rows without a phone can't satisfy the old NOT NULL constraint.
    op.execute("DELETE FROM app_user WHERE phone IS NULL")
    with op.batch_alter_table('app_user', reflect_args=_app_user_uuid_columns()) as batch:
        batch.drop_constraint('uq_app_user_auth_subject', type_='unique')
        batch.alter_column('phone', existing_type=sa.Text(), nullable=False)
        batch.drop_column('email')
        batch.drop_column('auth_subject')
