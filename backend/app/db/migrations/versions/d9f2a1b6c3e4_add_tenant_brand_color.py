"""add optional tenant brand color

Revision ID: d9f2a1b6c3e4
Revises: b4f1c7e82d10
Create Date: 2026-11-16 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9f2a1b6c3e4"
down_revision: Union[str, None] = "b4f1c7e82d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenant", sa.Column("brand_color", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenant", "brand_color")
