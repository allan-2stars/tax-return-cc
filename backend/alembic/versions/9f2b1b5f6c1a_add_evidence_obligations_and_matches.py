"""add evidence_obligations and evidence_matches

Revision ID: 9f2b1b5f6c1a
Revises: 4e7fcfe90ba9
Create Date: 2026-05-30 16:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f2b1b5f6c1a"
down_revision: Union[str, None] = "4e7fcfe90ba9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence_obligations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("financial_year", sa.String(length=10), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_id", sa.String(length=50), nullable=True),
        sa.Column("obligation_key", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("required_level", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "financial_year", "obligation_key", name="uq_evidence_obligation_ws_fy_key"),
    )
    op.create_index(op.f("ix_evidence_obligations_financial_year"), "evidence_obligations", ["financial_year"], unique=False)
    op.create_index(op.f("ix_evidence_obligations_obligation_key"), "evidence_obligations", ["obligation_key"], unique=False)
    op.create_index(op.f("ix_evidence_obligations_workspace_id"), "evidence_obligations", ["workspace_id"], unique=False)

    op.create_table(
        "evidence_matches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("obligation_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=True),
        sa.Column("tax_event_id", sa.String(length=36), nullable=True),
        sa.Column("match_type", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["obligation_id"], ["evidence_obligations.id"]),
        sa.ForeignKeyConstraint(["tax_event_id"], ["tax_events.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evidence_matches_document_id"), "evidence_matches", ["document_id"], unique=False)
    op.create_index(op.f("ix_evidence_matches_obligation_id"), "evidence_matches", ["obligation_id"], unique=False)
    op.create_index(op.f("ix_evidence_matches_tax_event_id"), "evidence_matches", ["tax_event_id"], unique=False)
    op.create_index(op.f("ix_evidence_matches_workspace_id"), "evidence_matches", ["workspace_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_evidence_matches_workspace_id"), table_name="evidence_matches")
    op.drop_index(op.f("ix_evidence_matches_tax_event_id"), table_name="evidence_matches")
    op.drop_index(op.f("ix_evidence_matches_obligation_id"), table_name="evidence_matches")
    op.drop_index(op.f("ix_evidence_matches_document_id"), table_name="evidence_matches")
    op.drop_table("evidence_matches")

    op.drop_index(op.f("ix_evidence_obligations_workspace_id"), table_name="evidence_obligations")
    op.drop_index(op.f("ix_evidence_obligations_obligation_key"), table_name="evidence_obligations")
    op.drop_index(op.f("ix_evidence_obligations_financial_year"), table_name="evidence_obligations")
    op.drop_table("evidence_obligations")
