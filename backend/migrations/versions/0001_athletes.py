"""Create athletes (worked example migration, agent-written).

Revision ID: 0001
Revises:
Create Date: 2026-09-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "athletes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("throwing_hand", sa.String(length=5), nullable=False),
        sa.Column("height_m", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.CheckConstraint("throwing_hand IN ('right', 'left')",
                           name=op.f("ck_athletes_throwing_hand")),
        sa.CheckConstraint("height_m IS NULL OR (height_m > 1.0 AND height_m < 2.5)",
                           name=op.f("ck_athletes_height_range")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_athletes")),
        sa.UniqueConstraint("code", name=op.f("uq_athletes_code")),
    )


def downgrade() -> None:
    op.drop_table("athletes")
