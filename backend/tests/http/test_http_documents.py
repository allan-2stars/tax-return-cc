"""HTTP smoke tests for /documents route group."""
import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Minimal valid PDF bytes — small enough for tests, valid enough that
# pdfplumber can open it without raising an exception.
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


@pytest.mark.asyncio
async def test_upload_pdf(auth_client):
    """POST /documents/upload with a valid PDF returns 200 with document_id."""
    resp = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "document_id" in body
    assert body["status"] == "processing"


@pytest.mark.asyncio
async def test_duplicate_detection(auth_client):
    """Uploading the same PDF twice returns duplicate status on the second upload."""
    await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("original.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    resp = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("copy.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "duplicate"
    assert "existing_document_id" in body


@pytest.mark.asyncio
async def test_get_documents(auth_client):
    """GET /documents returns 200 with a list (may be empty)."""
    resp = await auth_client.get("/api/v1/documents")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert isinstance(body["data"], list)


@pytest.mark.asyncio
async def test_document_summary(auth_client):
    """GET /documents/{id}/summary returns 200 with correct shape after upload."""
    upload = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("summary_test.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    doc_id = upload.json()["document_id"]

    resp = await auth_client.get(f"/api/v1/documents/{doc_id}/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    data = body["data"]
    assert data["document_id"] == doc_id
    assert "original_filename" in data
    assert "status" in data
    assert "file_size_bytes" in data


@pytest.mark.asyncio
async def test_upload_unsupported_format(auth_client):
    """POST /documents/upload with an .exe file returns 422 with unsupported_format."""
    resp = await auth_client.post(
        "/api/v1/documents/upload",
        files={"file": ("malware.exe", b"MZ\x90\x00this is an exe", "application/octet-stream")},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["error_code"] == "unsupported_format"


@pytest.mark.asyncio
async def test_document_stream_ready_reports_events_created(auth_client, test_engine):
    """SSE stream 'ready' payload reports real TaxEvent count for this document."""
    from app.db.models import Document, TaxEvent

    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        doc = Document(
            workspace_id=auth_client.workspace_id,
            financial_year="2024-25",
            original_filename="ready.pdf",
            storage_key="documents/ready.pdf",
            file_type="pdf",
            file_size_bytes=123,
            sha256_hash="0" * 64,
            status="ready",
        )
        session.add(doc)
        await session.flush()

        for i in range(2):
            session.add(
                TaxEvent(
                    workspace_id=auth_client.workspace_id,
                    document_id=doc.id,
                    financial_year="2024-25",
                    event_type="income",
                    category="payg_income",
                    description=f"Event {i}",
                    amount=100.0,
                    status="needs_user_review",
                )
            )

        await session.commit()

        resp = await auth_client.get(f"/api/v1/documents/{doc.id}/stream")
        assert resp.status_code == 200
        line = resp.text.strip().splitlines()[0]
        assert line.startswith("data: ")
        payload = json.loads(line[len("data: ") :])
        assert payload["status"] == "ready"
        assert payload["events_created"] == 2
