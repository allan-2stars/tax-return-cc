"""
Fix Pack 1: Upload pipeline closure tests.

Goals:
  1) When AI is available (mocked), upload -> extraction -> TaxEvent -> ReviewItem.
  2) When AI is unavailable, preserve OCR-only fallback (no TaxEvent creation).

No real Anthropic calls are made. AI is always mocked.
"""

import pytest
import pytest_asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


# Minimal valid PDF bytes, same shape as backend/tests/http/test_http_documents.py
_MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n"
    b"2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n"
    b"3 0 obj\n<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]>>\nendobj\n"
    b"xref\n0 4\n"
    b"0000000000 65535 f\n"
    b"0000000009 00000 n\n"
    b"0000000058 00000 n\n"
    b"0000000115 00000 n\n"
    b"trailer\n<</Size 4 /Root 1 0 R>>\n"
    b"startxref\n190\n%%EOF"
)


@pytest_asyncio.fixture(autouse=True)
async def _patch_async_session_local(test_engine, monkeypatch):
    """
    The documents extraction background worker uses app.db.base.AsyncSessionLocal
    directly (not the request-scoped get_db dependency override).

    Patch it to use the in-memory test_engine so _run_extraction() operates on
    the same DB as the HTTP client.
    """
    import app.db.base as db_base

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(db_base, "AsyncSessionLocal", maker)
    # routes/documents.py imports AsyncSessionLocal directly, so patch that alias too.
    import app.api.routes.documents as docs_routes
    monkeypatch.setattr(docs_routes, "AsyncSessionLocal", maker)


@pytest.mark.asyncio
async def test_upload_with_ai_creates_tax_events_and_review_items(auth_client, test_engine, tmp_path, monkeypatch):
    """
    Expected product behavior (Fix Pack 1):
      upload -> extraction -> AI classify -> skill.extract_events -> TaxEvent -> ReviewItem

    This is RED on current code:
      - /documents worker does not wire ai_adapter/review_engine/readiness_engine
      - EvidenceEngine uses registry.get_owner(skill_id), which cannot find the skill
    """
    from app.config import settings
    from app.db.models import Document, TaxEvent, ReviewItem
    from app.ai.base import ClassificationResult

    # Keep filesystem writes in a temp dir
    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))

    # Mock AI adapter creation to avoid any real API calls
    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="receipt",
                confidence=0.9,
                skill_id="employee_tax_au",
                suggested_category="work_expense",
                extracted_amounts=[{"amount": 120.0, "date": "2024-07-15", "description": "Work expense"}],
                notes="mocked",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    # Run the extraction worker directly (deterministic in tests)
    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        doc = (await session.execute(select(Document).where(Document.id == doc_id))).scalar_one()
        assert doc.status == "ready"

        event_count = (await session.execute(
            select(func.count(TaxEvent.id)).where(TaxEvent.document_id == doc_id)
        )).scalar() or 0
        item_count = (await session.execute(
            select(func.count(ReviewItem.id))
            .where(ReviewItem.workspace_id == auth_client.workspace_id)
        )).scalar() or 0

    assert event_count >= 1, "Expected at least 1 TaxEvent from uploaded document"
    assert item_count >= 1, "Expected at least 1 ReviewItem created for extracted TaxEvent"


@pytest.mark.asyncio
async def test_upload_without_ai_preserves_ocr_only_fallback(auth_client, test_engine, tmp_path, monkeypatch):
    """If AI is unavailable, the pipeline must still extract+mark ready but create no TaxEvents."""
    from app.config import settings
    from app.db.models import Document, TaxEvent

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")  # AI unavailable

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        doc = (await session.execute(select(Document).where(Document.id == doc_id))).scalar_one()
        assert doc.status == "ready"
        event_count = (await session.execute(
            select(func.count(TaxEvent.id)).where(TaxEvent.document_id == doc_id)
        )).scalar() or 0

    assert event_count == 0
