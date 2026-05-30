"""add rule_version to evidence_obligations

Revision ID: b3e4c5d6f7a8
Revises: a1d2e3f4b5c6
Create Date: 2026-05-30 23:50:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3e4c5d6f7a8"
down_revision: str | Sequence[str] | None = "a1d2e3f4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("evidence_obligations", sa.Column("rule_version", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("evidence_obligations", "rule_version")

