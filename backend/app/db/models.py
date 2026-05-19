from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, ForeignKey,
    Integer, JSON, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid4())


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    financial_year: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class TaxProfile(Base):
    __tablename__ = "tax_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    financial_year: Mapped[str] = mapped_column(String(10))
    employment_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    resident_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    user_lodger_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    has_wfh: Mapped[bool] = mapped_column(Boolean, default=False)
    has_investments: Mapped[bool] = mapped_column(Boolean, default=False)
    has_crypto: Mapped[bool] = mapped_column(Boolean, default=False)
    has_property: Mapped[bool] = mapped_column(Boolean, default=False)
    has_private_health: Mapped[bool] = mapped_column(Boolean, default=False)
    has_sole_trader: Mapped[bool] = mapped_column(Boolean, default=False)
    has_spouse: Mapped[bool] = mapped_column(Boolean, default=False)
    has_dependents: Mapped[bool] = mapped_column(Boolean, default=False)
    spouse_income_range: Mapped[str | None] = mapped_column(String(30), nullable=True)
    dependent_count: Mapped[int] = mapped_column(Integer, default=0)
    has_novated_lease: Mapped[bool] = mapped_column(Boolean, default=False)
    spouse_has_novated_lease: Mapped[bool] = mapped_column(Boolean, default=False)
    spouse_rfba_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    active_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    fy_end_reminder_set: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    financial_year: Mapped[str] = mapped_column(String(10))
    state: Mapped[str] = mapped_column(String(30), default="not_started")
    current_step: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    completed_steps: Mapped[list | None] = mapped_column(JSON, nullable=True)
    skipped_steps: Mapped[list | None] = mapped_column(JSON, nullable=True)
    branch_path: Mapped[list | None] = mapped_column(JSON, nullable=True)
    pending_queue: Mapped[list | None] = mapped_column(JSON, nullable=True)
    answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    activated_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    financial_year: Mapped[str] = mapped_column(String(10))
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), index=True)
    extraction_method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    document_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    skill_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="processing")
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    archived_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TaxEvent(Base):
    __tablename__ = "tax_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), index=True, nullable=True)
    financial_year: Mapped[str] = mapped_column(String(10))
    event_type: Mapped[str] = mapped_column(String(30))
    category: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="AUD")
    date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="document_extracted")
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    status: Mapped[str] = mapped_column(String(40), default="needs_user_review")
    review_status: Mapped[str] = mapped_column(String(30), default="pending")
    possible_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    user_action: Mapped[str | None] = mapped_column(String(30), nullable=True)
    user_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    amended_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    amended_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    skill_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    skill_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    group_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    group_display: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correction_history: Mapped[list | None] = mapped_column(JSON, nullable=True)
    inline_answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewItem(Base):
    __tablename__ = "review_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    tax_event_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tax_events.id"), index=True, nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    skill_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    inline_questions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    inline_answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    questions_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(40), default="needs_user_review")
    user_action: Mapped[str | None] = mapped_column(String(30), nullable=True)
    user_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    amended_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    amended_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    skipped_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ReadinessScore(Base):
    __tablename__ = "readiness_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    financial_year: Mapped[str] = mapped_column(String(10))
    percentage: Mapped[float] = mapped_column(Float, default=0.0)
    breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    missing_items: Mapped[list | None] = mapped_column(JSON, nullable=True)
    review_items: Mapped[list | None] = mapped_column(JSON, nullable=True)
    agent_items: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ExportRecord(Base):
    __tablename__ = "export_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    financial_year: Mapped[str] = mapped_column(String(10))
    readiness_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    confirmed_count: Mapped[int] = mapped_column(Integer, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    agent_count: Mapped[int] = mapped_column(Integer, default=0)
    missing_count: Mapped[int] = mapped_column(Integer, default=0)
    skills_active: Mapped[list | None] = mapped_column(JSON, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="generating")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class WorkspaceSecurity(Base):
    __tablename__ = "workspace_security"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_encrypted_dek: Mapped[str | None] = mapped_column(Text, nullable=True)
    recovery_key_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recovery_encrypted_dek: Mapped[str | None] = mapped_column(Text, nullable=True)
    unlock_session_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unlock_session_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    setup_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    recovery_confirm_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    tax_event_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tax_events.id"), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(50))
    actor: Mapped[str] = mapped_column(String(20))
    field: Mapped[str | None] = mapped_column(String(100), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_operation: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ai_provider: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class YoySuggestion(Base):
    __tablename__ = "yoy_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    source_workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    financial_year: Mapped[str] = mapped_column(String(10))
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount_last_year: Mapped[float | None] = mapped_column(Float, nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SkillVersionLock(Base):
    __tablename__ = "skill_version_locks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    skill_id: Mapped[str] = mapped_column(String(50))
    skill_version: Mapped[str] = mapped_column(String(20))
    locked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    feature: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    job_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TaxDeadlineReminder(Base):
    __tablename__ = "tax_deadline_reminders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    financial_year: Mapped[str] = mapped_column(String(10))
    deadline_type: Mapped[str] = mapped_column(String(20))
    deadline_date: Mapped[str] = mapped_column(String(10))
    reminders: Mapped[list | None] = mapped_column(JSON, nullable=True)


class EncryptedDraft(Base):
    __tablename__ = "encrypted_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), index=True)
    form_type: Mapped[str] = mapped_column(String(30))
    encrypted_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
