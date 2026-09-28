"""create monthly ENSO table

Revision ID: d1f3b8a4c620
Revises: 41be82e20b2f
Create Date: 2026-09-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1f3b8a4c620"
down_revision: Union[str, Sequence[str], None] = "41be82e20b2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "enso_mensal",
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("month", sa.SmallInteger(), nullable=False),
        sa.Column("enso_index", sa.Float(), nullable=True),
        sa.CheckConstraint("month BETWEEN 1 AND 12", name="ck_enso_mensal_month"),
        sa.PrimaryKeyConstraint("year", "month"),
    )


def downgrade() -> None:
    op.drop_table("enso_mensal")