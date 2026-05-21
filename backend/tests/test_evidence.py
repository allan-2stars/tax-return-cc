"""
Tests for EvidenceEngine (M3 pipeline).

pytesseract is always mocked — never run real OCR in the test suite.
pdfplumber is mocked to return controlled extracted text.
StorageBackend uses a real LocalStorageBackend with tmp_path.
"""
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.engines.evidence import EvidenceEngine
from app.errors import AppError
from app.repositories import documents as doc_repo
from app.storage.local import LocalStorageBackend


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def workspace(db_session):
    from app.db.models import Workspace
    ws = Workspace(name="Test WS", financial_year="2024-25", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest.fixture
def storage(tmp_path):
    return LocalStorageBackend(base_path=str(tmp_path))


@pytest_asyncio.fixture
async def engine(db_session, storage):
    return EvidenceEngine(db=db_session, storage=storage)


# ── file byte helpers ─────────────────────────────────────────────────────────

def _make_jpeg_bytes() -> bytes:
    img = Image.new("RGB", (1, 1), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_png_bytes() -> bytes:
    img = Image.new("RGB", (1, 1), color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\ntrailer\n<< /Root 1 0 R >>\n%%EOF"


def _make_csv_bytes(header: str, rows: list[str]) -> bytes:
    lines = [header] + rows
    return "\n".join(lines).encode()


COMMBANK_CSV = _make_csv_bytes(
    "Date,Amount,Description,Balance,Category",
    [
        "01/07/2024,-50.00,WOOLWORTHS SUPERMARKETS,1000.00,Groceries",
        "02/07/2024,3000.00,SALARY DEPOSIT,4000.00,Income",
    ],
)

CORRUPT_BYTES = b"\x00\xDE\xAD\xBE\xEF" * 20

OVERSIZED_PDF = _make_pdf_bytes() + b"x" * (21 * 1024 * 1024)  # 21 MB


# ── 1. valid PDF upload ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_valid_pdf_upload_creates_ready_document(engine, workspace):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Total income: $3000"
    mock_pdf = MagicMock()
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mock_pdf.pages = [mock_page]

    with patch("pdfplumber.open", return_value=mock_pdf):
        doc = await engine.validate_and_create(
            workspace_id=workspace.id,
            financial_year="2024-25",
            file_data=_make_pdf_bytes(),
            filename="income.pdf",
        )
        await engine.extract_and_finalize(doc.id)

    result = await doc_repo.get_by_id(engine._db, doc.id)
    assert result.status == "ready"
    assert result.extraction_method == "pdfplumber"
    assert result.extracted_text is not None
    assert engine.storage.exists(result.storage_key)


# ── 2. duplicate hash rejected ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_hash_rejected_with_zero_writes(engine, workspace):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "text"
    mock_pdf = MagicMock()
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mock_pdf.pages = [mock_page]

    pdf = _make_pdf_bytes()

    with patch("pdfplumber.open", return_value=mock_pdf):
        first = await engine.validate_and_create(
            workspace_id=workspace.id,
            financial_year="2024-25",
            file_data=pdf,
            filename="doc.pdf",
        )

    with pytest.raises(AppError) as exc_info:
        await engine.validate_and_create(
            workspace_id=workspace.id,
            financial_year="2024-25",
            file_data=pdf,
            filename="doc_copy.pdf",
        )

    err = exc_info.value
    assert err.error_code == "duplicate_document"
    assert err.existing_document_id == first.id

    # Only one Document record should exist
    from sqlalchemy import select, func
    from app.db.models import Document
    count_result = await engine._db.execute(
        select(func.count(Document.id)).where(Document.workspace_id == workspace.id)
    )
    assert count_result.scalar() == 1


# ── 3. corrupted file ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_corrupted_file_raises_file_corrupted(engine, workspace):
    with pytest.raises(AppError) as exc_info:
        await engine.validate_and_create(
            workspace_id=workspace.id,
            financial_year="2024-25",
            file_data=CORRUPT_BYTES,
            filename="corrupt.pdf",
        )
    assert exc_info.value.error_code == "unsupported_format"


# ── 4. file too large ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_file_too_large_raises_file_too_large(engine, workspace):
    with pytest.raises(AppError) as exc_info:
        await engine.validate_and_create(
            workspace_id=workspace.id,
            financial_year="2024-25",
            file_data=OVERSIZED_PDF,
            filename="huge.pdf",
        )
    assert exc_info.value.error_code == "file_too_large"


# ── 5. unsupported format ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unsupported_format_raises_unsupported_format(engine, workspace):
    # A valid ZIP file header — supported by libmagic but not by our allow-list
    zip_header = b"PK\x03\x04" + b"\x00" * 100
    with pytest.raises(AppError) as exc_info:
        await engine.validate_and_create(
            workspace_id=workspace.id,
            financial_year="2024-25",
            file_data=zip_header,
            filename="archive.zip",
        )
    assert exc_info.value.error_code == "unsupported_format"


# ── 6. CommBank CSV parsed correctly ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_commbank_csv_extracted_fields_populated(engine, workspace):
    doc = await engine.validate_and_create(
        workspace_id=workspace.id,
        financial_year="2024-25",
        file_data=COMMBANK_CSV,
        filename="commbank.csv",
    )
    await engine.extract_and_finalize(doc.id)

    result = await doc_repo.get_by_id(engine._db, doc.id)
    assert result.status == "ready"
    assert result.extraction_method == "csv_parse"
    assert result.extracted_fields is not None
    rows = result.extracted_fields.get("rows", [])
    assert len(rows) == 2
    assert result.extracted_fields.get("bank") == "commbank"


# ── 7. image falls back to tesseract ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_image_uses_tesseract_fallback(engine, workspace):
    with patch("pytesseract.image_to_string", return_value="OCR extracted text") as mock_tess:
        doc = await engine.validate_and_create(
            workspace_id=workspace.id,
            financial_year="2024-25",
            file_data=_make_jpeg_bytes(),
            filename="receipt.jpg",
        )
        await engine.extract_and_finalize(doc.id)

    mock_tess.assert_called_once()
    result = await doc_repo.get_by_id(engine._db, doc.id)
    assert result.status == "ready"
    assert result.extraction_method == "tesseract"
    assert result.extracted_text == "OCR extracted text"


# ── 8. sanitization removes sensitive numbers ────────────────────────────────

@pytest.mark.asyncio
async def test_sanitization_removes_tfn_bsb_account(engine, workspace):
    raw_text = "TFN: 123-456-789 BSB: 123456 Account: 12345678 Amount: $500"
    mock_page = MagicMock()
    mock_page.extract_text.return_value = raw_text
    mock_pdf = MagicMock()
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mock_pdf.pages = [mock_page]

    with patch("pdfplumber.open", return_value=mock_pdf):
        doc = await engine.validate_and_create(
            workspace_id=workspace.id,
            financial_year="2024-25",
            file_data=_make_pdf_bytes(),
            filename="statement.pdf",
        )
        await engine.extract_and_finalize(doc.id)

    result = await doc_repo.get_by_id(engine._db, doc.id)
    assert "123-456-789" not in result.extracted_text
    assert "[TFN]" in result.extracted_text
    assert "123456" not in result.extracted_text
    assert "[BSB]" in result.extracted_text
    assert "12345678" not in result.extracted_text
    assert "[ACCT]" in result.extracted_text
    assert "$500" in result.extracted_text  # amounts preserved


@pytest.mark.asyncio
async def test_list_documents_returns_empty_for_new_workspace(auth_client):
    """GET /documents returns empty list when no documents exist."""
    response = await auth_client.get("/api/v1/documents")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"] == []


@pytest.mark.asyncio
async def test_list_documents_excludes_archived(auth_client):
    """GET /documents excludes archived documents."""
    pdf_bytes = b"%PDF-1.4 minimal"
    response = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    doc_id = response.json()["document_id"]

    # Archive it
    del_response = await auth_client.delete(f"/api/v1/documents/{doc_id}")
    assert del_response.status_code == 200

    # Now list should be empty
    list_response = await auth_client.get("/api/v1/documents")
    assert list_response.status_code == 200
    assert list_response.json()["data"] == []


@pytest.mark.asyncio
async def test_archive_document_not_found(auth_client):
    """DELETE /documents/{id} returns 404 for unknown document."""
    response = await auth_client.delete("/api/v1/documents/nonexistent-id")
    assert response.status_code == 404
