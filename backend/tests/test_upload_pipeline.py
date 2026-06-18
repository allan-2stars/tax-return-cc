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


@pytest.mark.asyncio
async def test_upload_uses_workspace_financial_year(auth_client, test_engine, tmp_path, monkeypatch):
    """
    Fix Pack 1: /documents/upload must use Workspace.financial_year as the source of truth.
    """
    from app.config import settings
    from app.db.models import Document

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))

    # Create a second workspace for a different FY and switch the session to it.
    res = await auth_client.post(
        "/api/v1/workspaces",
        json={"name": "FY 2025-26", "financial_year": "2025-26"},
    )
    assert res.status_code == 200, res.text
    new_ws_id = res.json()["data"]["id"]

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("fy.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        doc = (await session.execute(select(Document).where(Document.id == doc_id))).scalar_one()

    assert doc.workspace_id == new_ws_id
    assert doc.financial_year == "2025-26"


@pytest.mark.asyncio
async def test_share_buy_contract_note_upload_creates_reviewable_event_and_item(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import ReviewItem, TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="share_buy_contract_note",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked investment classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "Broker: CommSec\n"
            "Stock Code: BHP\n"
            "Exchange: ASX\n"
            "Trade Date: 01/09/2024\n"
            "Settlement Date: 03/09/2024\n"
            "100 shares\n"
            "Price: $52.10\n"
            "Gross Amount: $5210.00\n"
            "Brokerage: $19.95\n",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("share-buy.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event = (
            await session.execute(
                select(TaxEvent).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()
        assert event.category == "shares_acquisition"
        assert event.event_type == "investment"
        assert event.event_metadata["stock_code"] == "BHP"
        assert event.event_metadata["units"] == 100.0
        assert event.event_metadata["price_per_unit"] == 52.10

        item = (
            await session.execute(
                select(ReviewItem).where(ReviewItem.tax_event_id == event.id)
            )
        ).scalar_one()
        assert item.category == "shares_acquisition"
        assert item.status == "needs_user_review"


@pytest.mark.asyncio
async def test_share_sell_contract_note_upload_creates_capital_gain_candidate_and_can_confirm(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import ReviewItem, TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="share_sell_contract_note",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked investment classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "Platform: Nabtrade\n"
            "Code: CBA\n"
            "ASX\n"
            "Trade Date: 10/04/2025\n"
            "Settlement Date: 14/04/2025\n"
            "Units: 50\n"
            "Price per unit: $120.40\n"
            "Gross Consideration: $6020.00\n"
            "Brokerage Fee: $14.95\n",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("share-sell.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event = (
            await session.execute(
                select(TaxEvent).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()
        assert event.category == "capital_gain_candidate"
        assert event.event_type == "investment"
        assert event.event_metadata["stock_code"] == "CBA"
        item = (
            await session.execute(
                select(ReviewItem).where(ReviewItem.tax_event_id == event.id)
            )
        ).scalar_one()
        item_id = item.id

    confirm = await auth_client.post(
        f"/api/v1/review/{item_id}/action",
        json={"action": "confirmed"},
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["data"]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_reprocessing_same_share_contract_note_does_not_duplicate_events(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="share_buy_contract_note",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked investment classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "Stock Code: BHP\n"
            "100 shares\n"
            "Price: $52.10\n"
            "Trade Date: 01/09/2024\n",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("share-buy-idempotent.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event_count = (
            await session.execute(
                select(func.count(TaxEvent.id)).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()

    assert event_count == 1


@pytest.mark.asyncio
async def test_unknown_share_contract_note_layout_does_not_crash_processing(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import Document, TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="share_buy_contract_note",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked investment classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "Unstructured broker note with no recognizable fields.",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("unknown-share-layout.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        doc = (await session.execute(select(Document).where(Document.id == doc_id))).scalar_one()
        event_count = (
            await session.execute(
                select(func.count(TaxEvent.id)).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()

    assert doc.status == "ready"
    assert event_count == 0


@pytest.mark.asyncio
async def test_partial_share_contract_note_extraction_still_creates_reviewable_output(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import ReviewItem, TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="share_buy_contract_note",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked investment classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "Stock Code: BHP\n"
            "100 shares\n"
            "Trade Date: 01/09/2024\n",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("partial-share-layout.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event = (
            await session.execute(
                select(TaxEvent).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()
        item = (
            await session.execute(
                select(ReviewItem).where(ReviewItem.tax_event_id == event.id)
            )
        ).scalar_one()

    assert event.category == "shares_acquisition"
    assert event.event_metadata["stock_code"] == "BHP"
    assert event.event_metadata["units"] == 100.0
    assert item.status == "needs_user_review"


@pytest.mark.asyncio
async def test_dividend_statement_upload_creates_dividend_event_and_review_item(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import ReviewItem, TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="share_dividend_statement",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked dividend classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "BHP Group Limited\n"
            "ASX Code: BHP\n"
            "Dividend: $145.20\n"
            "Franking Credits: $62.23\n"
            "Payment Date: 15 Sep 2025\n"
            "Record Date: 01 Sep 2025\n"
            "Shares Held: 200\n"
            "Currency: AUD\n",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("dividend.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event = (
            await session.execute(
                select(TaxEvent).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()
        assert event.category == "dividend"
        assert event.event_type == "investment"
        assert event.amount == 145.20
        assert event.event_metadata["company_name"] == "BHP Group Limited"
        assert event.event_metadata["stock_code"] == "BHP"
        assert event.event_metadata["franking_credits"] == 62.23
        assert event.event_metadata["payment_date"] == "2025-09-15"

        item = (
            await session.execute(
                select(ReviewItem).where(ReviewItem.tax_event_id == event.id)
            )
        ).scalar_one()
        assert item.category == "dividend"
        assert item.status == "needs_user_review"


@pytest.mark.asyncio
async def test_partial_dividend_statement_extraction_still_creates_reviewable_output(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import ReviewItem, TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="share_dividend_statement",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked dividend classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "Company: BHP Group Limited\n"
            "Dividend Amount: $145.20\n"
            "Payment Date: 15 Sep 2025\n",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("partial-dividend.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event = (
            await session.execute(
                select(TaxEvent).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()
        item = (
            await session.execute(
                select(ReviewItem).where(ReviewItem.tax_event_id == event.id)
            )
        ).scalar_one()

    assert event.category == "dividend"
    assert event.event_metadata["company_name"] == "BHP Group Limited"
    assert event.event_metadata["dividend_amount"] == 145.20
    assert "franking_credits" not in event.event_metadata
    assert item.status == "needs_user_review"


@pytest.mark.asyncio
async def test_reprocessing_same_dividend_statement_does_not_duplicate_events(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="share_dividend_statement",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked dividend classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "Company: BHP Group Limited\n"
            "Dividend Amount: $145.20\n"
            "Payment Date: 15 Sep 2025\n",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("dividend-idempotent.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event_count = (
            await session.execute(
                select(func.count(TaxEvent.id)).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()

    assert event_count == 1


@pytest.mark.asyncio
async def test_unknown_dividend_layout_does_not_crash_and_creates_no_event(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import Document, TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="share_dividend_statement",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked dividend classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "Registry correspondence with no recognizable dividend fields.",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("unknown-dividend-layout.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        doc = (await session.execute(select(Document).where(Document.id == doc_id))).scalar_one()
        event_count = (
            await session.execute(
                select(func.count(TaxEvent.id)).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()

    assert doc.status == "ready"
    assert event_count == 0


@pytest.mark.asyncio
async def test_managed_fund_statement_upload_creates_distribution_event_and_review_item(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import ReviewItem, TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="managed_fund_annual_tax_statement",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked managed fund classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "Vanguard Australian Shares Index Fund\n"
            "Fund Manager: Vanguard\n"
            "Distribution: $1,245.80\n"
            "Capital Gains: $215.40\n"
            "Foreign Income: $37.20\n"
            "TFN Withholding: $0.00\n"
            "Statement Date: 30 Jun 2025\n"
            "Financial Year: 2024-25\n",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("managed-fund.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event = (
            await session.execute(
                select(TaxEvent).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()
        assert event.category == "managed_fund_distribution"
        assert event.event_type == "investment"
        assert event.amount == 1245.80
        assert event.event_metadata["fund_name"] == "Vanguard Australian Shares Index Fund"
        assert event.event_metadata["capital_gains_component"] == 215.40
        assert event.event_metadata["foreign_income_component"] == 37.20
        assert event.event_metadata["tfn_withholding"] == 0.0
        assert event.event_metadata["statement_date"] == "2025-06-30"
        assert event.event_metadata["financial_year"] == "2024-25"

        item = (
            await session.execute(
                select(ReviewItem).where(ReviewItem.tax_event_id == event.id)
            )
        ).scalar_one()
        assert item.category == "managed_fund_distribution"
        assert item.status == "needs_user_review"


@pytest.mark.asyncio
async def test_partial_managed_fund_statement_extraction_still_creates_reviewable_output(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import ReviewItem, TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="managed_fund_annual_tax_statement",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked managed fund classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "Fund Name: Vanguard Australian Shares Index Fund\n"
            "Distribution Amount: $1,245.80\n"
            "Statement Date: 30 Jun 2025\n",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("partial-managed-fund.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event = (
            await session.execute(
                select(TaxEvent).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()
        item = (
            await session.execute(
                select(ReviewItem).where(ReviewItem.tax_event_id == event.id)
            )
        ).scalar_one()

    assert event.category == "managed_fund_distribution"
    assert event.event_metadata["fund_name"] == "Vanguard Australian Shares Index Fund"
    assert event.event_metadata["distribution_amount"] == 1245.80
    assert "capital_gains_component" not in event.event_metadata
    assert "foreign_income_component" not in event.event_metadata
    assert "tfn_withholding" not in event.event_metadata
    assert item.status == "needs_user_review"


@pytest.mark.asyncio
async def test_reprocessing_same_managed_fund_statement_does_not_duplicate_events(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="managed_fund_annual_tax_statement",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked managed fund classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "Fund Name: Vanguard Australian Shares Index Fund\n"
            "Distribution Amount: $1,245.80\n"
            "Statement Date: 30 Jun 2025\n",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("managed-fund-idempotent.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event_count = (
            await session.execute(
                select(func.count(TaxEvent.id)).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()

    assert event_count == 1


@pytest.mark.asyncio
async def test_unknown_managed_fund_layout_does_not_crash_and_creates_no_event(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import Document, TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="managed_fund_annual_tax_statement",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked managed fund classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "Investor correspondence with no recognizable tax statement fields.",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("unknown-managed-fund-layout.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        doc = (await session.execute(select(Document).where(Document.id == doc_id))).scalar_one()
        event_count = (
            await session.execute(
                select(func.count(TaxEvent.id)).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()

    assert doc.status == "ready"
    assert event_count == 0


@pytest.mark.asyncio
async def test_broker_summary_upload_creates_share_annual_summary_event_and_review_item(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import ReviewItem, TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="share_annual_broker_summary",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked broker summary classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "Broker: SelfWealth\n"
            "Financial Year: 2024-25\n"
            "Buy Transactions: 12\n"
            "Sell Transactions: 7\n"
            "Purchases: $12,400\n"
            "Sales: $8,700\n"
            "Dividends: $640\n"
            "Brokerage: $95\n"
            "Holdings Count: 5\n",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("broker-summary.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event = (
            await session.execute(
                select(TaxEvent).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()
        assert event.category == "share_annual_summary"
        assert event.event_type == "investment"
        assert event.event_metadata["broker_name"] == "SelfWealth"
        assert event.event_metadata["financial_year"] == "2024-25"
        assert event.event_metadata["total_purchase_value"] == 12400.0
        assert event.event_metadata["total_sale_value"] == 8700.0
        assert event.event_metadata["total_dividend_income"] == 640.0
        assert event.event_metadata["total_brokerage_fees"] == 95.0

        item = (
            await session.execute(
                select(ReviewItem).where(ReviewItem.tax_event_id == event.id)
            )
        ).scalar_one()
        assert item.category == "share_annual_summary"
        assert item.status == "needs_user_review"


@pytest.mark.asyncio
async def test_partial_broker_summary_extraction_still_creates_reviewable_output(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import ReviewItem, TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="share_annual_broker_summary",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked broker summary classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "Broker: SelfWealth\n"
            "FY: 2024-25\n"
            "Dividends: $640\n",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("partial-broker-summary.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event = (
            await session.execute(
                select(TaxEvent).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()
        item = (
            await session.execute(
                select(ReviewItem).where(ReviewItem.tax_event_id == event.id)
            )
        ).scalar_one()

    assert event.category == "share_annual_summary"
    assert event.event_metadata["broker_name"] == "SelfWealth"
    assert event.event_metadata["financial_year"] == "2024-25"
    assert event.event_metadata["total_dividend_income"] == 640.0
    assert "total_brokerage_fees" not in event.event_metadata
    assert item.status == "needs_user_review"


@pytest.mark.asyncio
async def test_reprocessing_same_broker_summary_does_not_duplicate_events(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="share_annual_broker_summary",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked broker summary classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "Broker: SelfWealth\n"
            "FY: 2024-25\n"
            "Dividends: $640\n",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("broker-summary-idempotent.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        event_count = (
            await session.execute(
                select(func.count(TaxEvent.id)).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()

    assert event_count == 1


@pytest.mark.asyncio
async def test_unknown_broker_summary_layout_does_not_crash_and_creates_no_event(auth_client, test_engine, tmp_path, monkeypatch):
    from app.config import settings
    from app.db.models import Document, TaxEvent
    from app.ai.base import ClassificationResult

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key-present")

    class _FakeAdapter:
        async def classify(self, text: str, fields: dict | None, profile: dict | None) -> ClassificationResult:
            return ClassificationResult(
                document_type="share_annual_broker_summary",
                confidence=0.92,
                skill_id="investment_skill",
                suggested_category=None,
                extracted_amounts=[],
                notes="mocked broker summary classification",
            )

    import app.ai as ai_mod
    monkeypatch.setattr(ai_mod, "get_ai_adapter", lambda workspace_id="": _FakeAdapter())

    from app.engines.evidence import EvidenceEngine
    monkeypatch.setattr(
        EvidenceEngine,
        "_extract_pdf",
        lambda self, doc: (
            "General broker correspondence with no recognizable annual summary fields.",
            {},
            "pdfplumber",
            0.95,
        ),
    )

    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("unknown-broker-summary.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["document_id"]

    from app.api.routes.documents import _run_extraction
    await _run_extraction(doc_id)

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        doc = (await session.execute(select(Document).where(Document.id == doc_id))).scalar_one()
        event_count = (
            await session.execute(
                select(func.count(TaxEvent.id)).where(TaxEvent.document_id == doc_id)
            )
        ).scalar_one()

    assert doc.status == "ready"
    assert event_count == 0
