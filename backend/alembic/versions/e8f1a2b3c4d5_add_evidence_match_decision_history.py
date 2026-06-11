"""add evidence match decision history

Revision ID: e8f1a2b3c4d5
Revises: c4d5e6f7a8b9
Create Date: 2026-06-10 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e8f1a2b3c4d5"
down_revision: str | Sequence[str] | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_match_decision_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("evidence_match_id", sa.String(length=36), nullable=False),
        sa.Column("evidence_obligation_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("actor", sa.String(length=20), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["evidence_match_id"], ["evidence_matches.id"]),
        sa.ForeignKeyConstraint(["evidence_obligation_id"], ["evidence_obligations.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evidence_match_decision_history_workspace_id"),
        "evidence_match_decision_history",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evidence_match_decision_history_evidence_match_id"),
        "evidence_match_decision_history",
        ["evidence_match_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evidence_match_decision_history_evidence_obligation_id"),
        "evidence_match_decision_history",
        ["evidence_obligation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_evidence_match_decision_history_evidence_obligation_id"),
        table_name="evidence_match_decision_history",
    )
    op.drop_index(
        op.f("ix_evidence_match_decision_history_evidence_match_id"),
        table_name="evidence_match_decision_history",
    )
    op.drop_index(
        op.f("ix_evidence_match_decision_history_workspace_id"),
        table_name="evidence_match_decision_history",
    )
    op.drop_table("evidence_match_decision_history")
