"""user_id

Revision ID: 0003_user_id
Revises: 0002_profiles
Create Date: 2026-10-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_user_id"
down_revision = "0002_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "predictions",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
            index=True,
        ),
    )
    op.add_column(
        "predictions_v2",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("predictions_v2", "user_id")
    op.drop_column("predictions", "user_id")
