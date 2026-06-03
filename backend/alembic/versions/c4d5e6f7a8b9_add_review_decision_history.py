"""add review decision history

Revision ID: c4d5e6f7a8b9
Revises: b3e4c5d6f7a8
Create Date: 2026-06-03 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: str | Sequence[str] | None = "b3e4c5d6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_decision_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("review_item_id", sa.String(length=36), nullable=False),
        sa.Column("tax_event_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("actor", sa.String(length=20), nullable=False),
        sa.Column("previous_status", sa.String(length=40), nullable=True),
        sa.Column("new_status", sa.String(length=40), nullable=True),
        sa.Column("changed_fields", sa.JSON(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("bulk_action_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["review_item_id"], ["review_items.id"]),
        sa.ForeignKeyConstraint(["tax_event_id"], ["tax_events.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_review_decision_history_workspace_id"),
        "review_decision_history",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_decision_history_review_item_id"),
        "review_decision_history",
        ["review_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_decision_history_tax_event_id"),
        "review_decision_history",
        ["tax_event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_decision_history_bulk_action_id"),
        "review_decision_history",
        ["bulk_action_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_review_decision_history_bulk_action_id"), table_name="review_decision_history")
    op.drop_index(op.f("ix_review_decision_history_tax_event_id"), table_name="review_decision_history")
    op.drop_index(op.f("ix_review_decision_history_review_item_id"), table_name="review_decision_history")
    op.drop_index(op.f("ix_review_decision_history_workspace_id"), table_name="review_decision_history")
    op.drop_table("review_decision_history")
