"""add workspace evidence reconcile fields

Revision ID: a1d2e3f4b5c6
Revises: 9f2b1b5f6c1a
Create Date: 2026-05-30 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1d2e3f4b5c6"
down_revision: str | Sequence[str] | None = "9f2b1b5f6c1a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("workspaces", "evidence_reconciled_at"):
        op.add_column("workspaces", sa.Column("evidence_reconciled_at", sa.DateTime(timezone=True), nullable=True))
    if not _has_column("workspaces", "evidence_reconcile_status"):
        op.add_column("workspaces", sa.Column("evidence_reconcile_status", sa.String(length=20), nullable=False, server_default="idle"))
        op.alter_column("workspaces", "evidence_reconcile_status", server_default=None)
    if not _has_column("workspaces", "evidence_reconcile_meta"):
        op.add_column("workspaces", sa.Column("evidence_reconcile_meta", sa.JSON(), nullable=True))


def downgrade() -> None:
    if _has_column("workspaces", "evidence_reconcile_meta"):
        op.drop_column("workspaces", "evidence_reconcile_meta")
    if _has_column("workspaces", "evidence_reconcile_status"):
        op.drop_column("workspaces", "evidence_reconcile_status")
    if _has_column("workspaces", "evidence_reconciled_at"):
        op.drop_column("workspaces", "evidence_reconciled_at")
