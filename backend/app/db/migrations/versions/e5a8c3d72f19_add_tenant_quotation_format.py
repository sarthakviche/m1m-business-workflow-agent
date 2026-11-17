"""add optional custom quotation format

Revision ID: e5a8c3d72f19
Revises: d9f2a1b6c3e4
Create Date: 2026-11-17 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5a8c3d72f19"
down_revision: Union[str, None] = "d9f2a1b6c3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The business's own quotation layout, read from a sample they uploaded.
    # NULL means Munim's standard quotation.
    op.add_column("tenant", sa.Column("quotation_format", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenant", "quotation_format")
