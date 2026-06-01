"""
Tests for M9 Export Engine — TDD (all tests written before implementation).
"""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import (
    BackgroundJob,
    Document,
    EvidenceObligation,
    ExportRecord,
    InterviewSession,
    ReviewItem,
    TaxEvent,
    Workspace,
)
from app.services.evidence_rules import CURRENT_EVIDENCE_RULE_VERSION


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def patch_async_session_local(test_engine, monkeypatch):
    import app.db.base as db_base
    test_maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(db_base, "AsyncSessionLocal", test_maker)


@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def workspace(db_session):
    ws = Workspace(name="Export Test WS", financial_year="2024-25", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


# ── helpers ───────────────────────────────────────────────────────────────────

async def _create_event(
    db,
    workspace_id: str,
    status: str = "confirmed",
    event_type: str = "income",
    category: str = "payg_income",
    amount: float = 5000.0,
) -> TaxEvent:
    ev = TaxEvent(
        workspace_id=workspace_id,
        financial_year="2024-25",
        event_type=event_type,
        category=category,
        description="Test event",
        amount=amount,
        status=status,
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return ev


async def _create_document(
    db,
    workspace_id: str,
    status: str = "ready",
    archived: bool = False,
) -> Document:
    doc = Document(
        workspace_id=workspace_id,
        financial_year="2024-25",
        original_filename="test.pdf",
        storage_key=f"{workspace_id}/doc1/original.pdf",
        file_type="pdf",
        sha256_hash="ab" * 32,
        status=status,
        archived=archived,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def _create_interview_session(
    db,
    workspace_id: str,
    state: str = "complete",
    answers: dict | None = None,
    skipped_steps: list | None = None,
) -> InterviewSession:
    sess = InterviewSession(
        workspace_id=workspace_id,
        financial_year="2024-25",
        state=state,
        answers=answers or {},
        activated_skills=[],
        pending_queue=[],
        completed_steps=[],
        skipped_steps=skipped_steps or [],
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    return sess


async def _create_review_item(
    db, workspace_id: str, status: str = "needs_user_review"
) -> ReviewItem:
    item = ReviewItem(
        workspace_id=workspace_id,
        category="work_expense",
        amount=100.0,
        risk_level="low",
        status=status,
        questions_complete=True,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


def _mock_zipper():
    mock_zf = MagicMock()
    mock_pz = MagicMock()
    mock_pz.AESZipFile.return_value.__enter__.return_value = mock_zf
    mock_pz.AESZipFile.return_value.__exit__.return_value = False
    mock_pz.ZIP_DEFLATED = 8
    mock_pz.WZ_AES = 99
    return mock_pz, mock_zf


async def _run_export_inline(coro):
    await coro


# ── 1. eligibility blocked — interview not complete ───────────────────────────

@pytest.mark.asyncio
async def test_check_eligibility_blocked_interview_not_complete(workspace, db_session):
    from app.engines.export import ExportEngine

    await _create_interview_session(db_session, workspace.id, state="in_progress")
    await _create_event(db_session, workspace.id, status="confirmed")

    engine = ExportEngine()
    result = await engine.check_eligibility(workspace.id, db_session)

    assert result.can_export is False
    assert any("interview" in r.lower() for r in result.blocking_reasons)


@pytest.mark.asyncio
async def test_check_eligibility_blocked_when_journey_has_incomplete_required_questions(workspace, db_session):
    from app.engines.export import ExportEngine

    await _create_interview_session(
        db_session,
        workspace.id,
        state="awaiting_evidence",
        answers={"residency": "resident"},
        skipped_steps=[{"question_id": "fy_confirm", "reason": "skip_for_now"}],
    )
    await _create_event(db_session, workspace.id, status="confirmed")

    engine = ExportEngine()
    result = await engine.check_eligibility(workspace.id, db_session)

    assert result.can_export is False
    assert any("complete your tax journey" in r.lower() for r in result.blocking_reasons)


@pytest.mark.asyncio
async def test_check_eligibility_allows_when_skipped_question_later_answered(workspace, db_session):
    from app.engines.export import ExportEngine

    await _create_interview_session(
        db_session,
        workspace.id,
        state="awaiting_evidence",
        answers={"fy_confirm": "2024-25", "residency": "resident"},
        skipped_steps=[{"question_id": "fy_confirm", "reason": "skip_for_now"}],
    )
    await _create_event(db_session, workspace.id, status="confirmed")

    engine = ExportEngine()
    result = await engine.check_eligibility(workspace.id, db_session)

    assert result.can_export is True
    assert not any("complete your tax journey" in r.lower() for r in result.blocking_reasons)


# ── 2. eligibility blocked — no confirmed events ──────────────────────────────

@pytest.mark.asyncio
async def test_check_eligibility_blocked_no_confirmed_events(workspace, db_session):
    from app.engines.export import ExportEngine

    await _create_interview_session(db_session, workspace.id, state="complete")
    await _create_event(db_session, workspace.id, status="needs_user_review")

    engine = ExportEngine()
    result = await engine.check_eligibility(workspace.id, db_session)

    assert result.can_export is False
    assert any("confirmed" in r.lower() for r in result.blocking_reasons)


# ── 3. eligibility blocked — documents still processing ──────────────────────

@pytest.mark.asyncio
async def test_check_eligibility_blocked_documents_processing(workspace, db_session):
    from app.engines.export import ExportEngine

    await _create_interview_session(db_session, workspace.id, state="complete")
    await _create_event(db_session, workspace.id, status="confirmed")
    await _create_document(db_session, workspace.id, status="processing")

    engine = ExportEngine()
    result = await engine.check_eligibility(workspace.id, db_session)

    assert result.can_export is False
    assert any("processing" in r.lower() for r in result.blocking_reasons)


# ── 4. eligibility warns — pending review items (not a hard block) ────────────

@pytest.mark.asyncio
async def test_check_eligibility_warns_pending_review_items(workspace, db_session):
    from app.engines.export import ExportEngine

    await _create_interview_session(db_session, workspace.id, state="complete")
    await _create_event(db_session, workspace.id, status="confirmed")
    await _create_review_item(db_session, workspace.id, status="needs_user_review")

    engine = ExportEngine()
    result = await engine.check_eligibility(workspace.id, db_session)

    assert result.can_export is True
    assert len(result.warnings) > 0


# ── 5. generate() creates BackgroundJob + ExportRecord ────────────────────────

@pytest.mark.asyncio
async def test_generate_creates_background_job_and_export_record(workspace, db_session):
    from app.engines.export import ExportEngine

    await _create_interview_session(db_session, workspace.id, state="complete")
    await _create_event(db_session, workspace.id, status="confirmed")

    mock_pz, _ = _mock_zipper()
    with patch("app.engines.export.HTML") as mock_html, \
         patch("app.engines.export.pyzipper", mock_pz), \
         patch("app.engines.export.asyncio.create_task") as mock_create_task:
        mock_html.return_value.write_pdf.return_value = b"PDF"
        mock_create_task.side_effect = lambda coro: coro.close()  # prevent background task leakage in tests
        engine = ExportEngine()
        record = await engine.generate(workspace.id, "test-password", db_session)

    # Check immediately — background task has not yet run
    assert record.status == "generating"
    assert record.workspace_id == workspace.id
    assert record.id is not None

    job_result = await db_session.execute(
        select(BackgroundJob).where(
            BackgroundJob.workspace_id == workspace.id,
            BackgroundJob.job_type == "export_generate",
        )
    )
    job = job_result.scalar_one_or_none()
    assert job is not None
    assert job.status in ("pending", "running")


@pytest.mark.asyncio
async def test_generate_includes_export_id_in_job_payload(workspace, db_session):
    from app.engines.export import ExportEngine

    await _create_interview_session(db_session, workspace.id, state="complete")
    await _create_event(db_session, workspace.id, status="confirmed")

    mock_pz, _ = _mock_zipper()
    with patch("app.engines.export.HTML") as mock_html, \
         patch("app.engines.export.pyzipper", mock_pz), \
         patch("app.engines.export.asyncio.create_task") as mock_create_task:
        mock_html.return_value.write_pdf.return_value = b"PDF"
        mock_create_task.side_effect = lambda coro: coro.close()  # prevent background task leakage in tests
        engine = ExportEngine()
        record = await engine.generate(workspace.id, "test-password", db_session)

    job_result = await db_session.execute(
        select(BackgroundJob).where(
            BackgroundJob.workspace_id == workspace.id,
            BackgroundJob.job_type == "export_generate",
        )
    )
    job = job_result.scalar_one()
    assert job.payload is not None
    assert job.payload.get("export_id") == record.id


@pytest.mark.asyncio
async def test_reconcile_marks_stale_generating_export_failed(workspace, db_session):
    from app.engines.export import ExportEngine

    stale_created = datetime.now(timezone.utc) - timedelta(seconds=700)

    record = ExportRecord(
        workspace_id=workspace.id,
        financial_year="2024-25",
        status="generating",
        created_at=stale_created,
    )
    db_session.add(record)
    await db_session.flush()

    job = BackgroundJob(
        workspace_id=workspace.id,
        job_type="export_generate",
        status="running",
        payload={"export_id": record.id},
        created_at=stale_created,
    )
    db_session.add(job)
    await db_session.commit()

    engine = ExportEngine()
    updated = await engine.reconcile_stale_exports(db_session, stale_after_seconds=600)
    assert updated >= 1

    await db_session.refresh(record)
    assert record.status == "failed"

    await db_session.refresh(job)
    assert job.status == "failed"
    assert job.error == "Export interrupted (server restart or worker shutdown). Please generate again."


# ── 6. background task completes and ExportRecord becomes "ready" ─────────────

@pytest.mark.asyncio
async def test_generate_package_structure_correct(workspace, db_session, tmp_path):
    from app.engines.export import ExportEngine

    await _create_interview_session(db_session, workspace.id, state="complete")
    await _create_event(db_session, workspace.id, status="confirmed")

    mock_pz, mock_zf = _mock_zipper()
    mock_storage = MagicMock()
    mock_storage.get.return_value = b"fake-file-content"

    with patch("app.engines.export.HTML") as mock_html, \
         patch("app.engines.export.pyzipper", mock_pz):
        mock_html.return_value.write_pdf.return_value = b"PDF"
        engine = ExportEngine(
            export_path=str(tmp_path),
            storage=mock_storage,
            export_task_runner=_run_export_inline,
        )
        record = await engine.generate(workspace.id, "test-password", db_session)

    await db_session.refresh(record)
    assert record.status == "ready"

    # WeasyPrint called for cover, summary, missing (3 PDF pages)
    assert mock_html.return_value.write_pdf.call_count == 3


# ── 7. cleanup_expired marks records expired and deletes files ────────────────

@pytest.mark.asyncio
async def test_cleanup_expired_marks_records_expired_and_deletes_files(
    workspace, db_session, tmp_path
):
    from app.engines.export import ExportEngine

    zip_dir = tmp_path / workspace.id
    zip_dir.mkdir(parents=True)
    fake_zip = zip_dir / "expiredexport.zip"
    fake_zip.write_bytes(b"fake zip content")

    past_time = datetime.now(timezone.utc) - timedelta(hours=48)
    export_rec = ExportRecord(
        workspace_id=workspace.id,
        financial_year="2024-25",
        storage_key=f"{workspace.id}/expiredexport.zip",
        status="ready",
        expires_at=past_time,
    )
    db_session.add(export_rec)
    await db_session.commit()
    await db_session.refresh(export_rec)

    engine = ExportEngine(export_path=str(tmp_path))
    expired_count = await engine.cleanup_expired(db_session)

    assert expired_count == 1
    assert not fake_zip.exists()

    await db_session.refresh(export_rec)
    assert export_rec.status == "expired"


# ── 8. zip contains all required files (exhaustive structure check) ───────────

@pytest.mark.asyncio
async def test_export_zip_contains_all_required_files(workspace, db_session, tmp_path):
    from app.engines.export import ExportEngine

    await _create_interview_session(db_session, workspace.id, state="complete")
    await _create_event(db_session, workspace.id, status="confirmed")

    REQUIRED_FILES = [
        "00-COVER.pdf",
        "01-TAX-EVENTS.json",
        "02-REVIEW-SUMMARY.pdf",
        "03-MISSING-ITEMS.pdf",
        "04-AI-REASONING.json",
        "04A-REVIEW-ITEMS.json",
        "05-AUDIT-LOG.json",
        "05A-EVIDENCE-STATUS.json",
        "06-SCHEMA-VERSION.txt",
        "07-DISCLAIMER.txt",
        "evidence/manifest.json",
    ]

    mock_pz, mock_zf = _mock_zipper()

    with patch("app.engines.export.HTML") as mock_html, \
         patch("app.engines.export.pyzipper", mock_pz):
        mock_html.return_value.write_pdf.return_value = b"PDF"
        engine = ExportEngine(
            export_path=str(tmp_path),
            storage=MagicMock(),
            export_task_runner=_run_export_inline,
        )
        await engine.generate(workspace.id, "test-password", db_session)

    written_names = {args[0] for args, _ in mock_zf.writestr.call_args_list}
    for req in REQUIRED_FILES:
        assert req in written_names, f"Missing required file in zip: {req}"

    evidence_status_calls = [
        args for args, _ in mock_zf.writestr.call_args_list if args[0] == "05A-EVIDENCE-STATUS.json"
    ]
    assert len(evidence_status_calls) == 1
    payload = evidence_status_calls[0][1]
    data = payload if isinstance(payload, dict) else json.loads(payload)
    assert data["current_rule_version"] == CURRENT_EVIDENCE_RULE_VERSION
    assert "summary" in data


@pytest.mark.asyncio
async def test_export_review_items_json_includes_explanations(workspace, db_session, tmp_path):
    from app.engines.export import ExportEngine

    event = await _create_event(
        db_session,
        workspace.id,
        status="confirmed",
        event_type="deduction",
        category="work_expense",
    )
    await _create_interview_session(db_session, workspace.id, state="complete")
    review_item = ReviewItem(
        workspace_id=workspace.id,
        tax_event_id=event.id,
        title="Work expense item",
        category="work_expense",
        amount=100.0,
        date="2025-07-01",
        status="needs_user_review",
        risk_level="low",
        questions_complete=True,
    )
    db_session.add(review_item)
    await db_session.commit()

    mock_pz, mock_zf = _mock_zipper()
    with patch("app.engines.export.HTML") as mock_html, \
         patch("app.engines.export.pyzipper", mock_pz):
        mock_html.return_value.write_pdf.return_value = b"PDF"
        engine = ExportEngine(
            export_path=str(tmp_path),
            storage=MagicMock(),
            export_task_runner=_run_export_inline,
        )
        await engine.generate(workspace.id, "test-password", db_session)

    review_calls = [args for args, _ in mock_zf.writestr.call_args_list if args[0] == "04A-REVIEW-ITEMS.json"]
    assert len(review_calls) == 1
    payload = review_calls[0][1]
    data = payload if isinstance(payload, list) else json.loads(payload)
    assert isinstance(data, list)
    assert len(data) >= 1
    target = next(item for item in data if item["id"] == review_item.id)
    assert "explanation" in target
    assert target["explanation"]["plain_english_summary"]
    assert target["explanation"]["why_it_matters"]
    assert target["explanation"]["what_user_should_check"]
    assert isinstance(target["explanation"]["evidence_expected"], list)
    assert target["explanation"]["confidence_level"] in {"low", "medium", "high"}
    assert target["explanation"]["source"] == "review"


@pytest.mark.asyncio
async def test_export_evidence_status_includes_obligation_explanations(workspace, db_session, tmp_path):
    from app.engines.export import ExportEngine

    await _create_event(db_session, workspace.id, status="confirmed")
    await _create_interview_session(db_session, workspace.id, state="complete")
    db_session.add(
        EvidenceObligation(
            workspace_id=workspace.id,
            financial_year="2024-25",
            source_type="tax_event",
            source_id=None,
            obligation_key="work_expense_receipt",
            category="work_expense",
            label="Work expense receipt",
            required_level="required",
            status="missing",
            rule_version=CURRENT_EVIDENCE_RULE_VERSION,
        )
    )
    await db_session.commit()

    mock_pz, mock_zf = _mock_zipper()
    with patch("app.engines.export.HTML") as mock_html, \
         patch("app.engines.export.pyzipper", mock_pz):
        mock_html.return_value.write_pdf.return_value = b"PDF"
        engine = ExportEngine(
            export_path=str(tmp_path),
            storage=MagicMock(),
            export_task_runner=_run_export_inline,
        )
        await engine.generate(workspace.id, "test-password", db_session)

    evidence_status_calls = [
        args for args, _ in mock_zf.writestr.call_args_list if args[0] == "05A-EVIDENCE-STATUS.json"
    ]
    assert len(evidence_status_calls) == 1
    payload = evidence_status_calls[0][1]
    data = payload if isinstance(payload, dict) else json.loads(payload)
    obligations = data["incomplete_required_obligations"]
    assert len(obligations) >= 1
    first = obligations[0]
    assert "explanation" in first
    assert first["explanation"]["source"] == "rule"
    assert first["explanation"]["rule_version"] == CURRENT_EVIDENCE_RULE_VERSION
    assert first["explanation"]["plain_english_summary"]
