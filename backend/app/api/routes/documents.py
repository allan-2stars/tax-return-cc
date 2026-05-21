import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_auth
from app.db.base import AsyncSessionLocal, get_db
from app.engines.evidence import EvidenceEngine
from app.errors import AppError, DuplicateDocumentError, error_response
from app.repositories import documents as doc_repo
from app.storage import get_storage_backend

logger = logging.getLogger(__name__)
router = APIRouter()

_SSE_POLL_INTERVAL = 1.5   # seconds between DB polls
_SSE_TIMEOUT = 300          # 5-minute max hold — prevents stuck jobs from leaking connections


async def _run_extraction(document_id: str) -> None:
    """Background task: creates its own DB session, independent of the request session."""
    storage = get_storage_backend()
    async with AsyncSessionLocal() as db:
        engine = EvidenceEngine(db=db, storage=storage)
        await engine.extract_and_finalize(document_id)


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    file_data = await file.read()
    filename = file.filename or "upload"
    storage = get_storage_backend()
    engine = EvidenceEngine(db=db, storage=storage)

    try:
        doc = await engine.validate_and_create(
            workspace_id=workspace_id,
            financial_year="2024-25",
            file_data=file_data,
            filename=filename,
        )
    except DuplicateDocumentError as e:
        return {"status": "duplicate", "existing_document_id": e.existing_document_id}
    except AppError as e:
        raise HTTPException(
            status_code=422,
            detail=error_response(e.error_code, e.message, e.action, e.retryable),
        )

    background_tasks.add_task(_run_extraction, doc.id)
    return {"document_id": doc.id, "status": "processing"}


@router.get("/documents")
async def list_documents(
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    docs = await doc_repo.list_by_workspace(db, workspace_id)
    return {
        "status": "ok",
        "data": [
            {
                "document_id": d.id,
                "original_filename": d.original_filename,
                "file_type": d.file_type,
                "file_size_bytes": d.file_size_bytes,
                "status": d.status,
                "document_type": d.document_type,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
                "processed_at": d.processed_at.isoformat() if d.processed_at else None,
            }
            for d in docs
        ],
    }


@router.get("/documents/{document_id}/stream")
async def stream_document_progress(
    document_id: str,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    async def _event_stream():
        loop = asyncio.get_event_loop()
        deadline = loop.time() + _SSE_TIMEOUT

        while True:
            if loop.time() >= deadline:
                yield f"data: {json.dumps({'document_id': document_id, 'status': 'failed', 'error_code': 'processing_timeout'})}\n\n"
                return

            doc = await doc_repo.get_by_id(db, document_id)
            if doc is None or doc.workspace_id != workspace_id:
                yield f"data: {json.dumps({'document_id': document_id, 'status': 'failed', 'error_code': 'not_found'})}\n\n"
                return

            if doc.status in ("ready", "failed", "archived"):
                if doc.status == "ready":
                    payload = {"document_id": document_id, "status": "ready", "events_created": 0}
                elif doc.status == "failed":
                    payload = {"document_id": document_id, "status": "failed", "error_code": "processing_failed"}
                else:
                    payload = {"document_id": document_id, "status": "archived", "error_code": "archived"}
                yield f"data: {json.dumps(payload)}\n\n"
                return

            yield f"data: {json.dumps({'document_id': document_id, 'status': 'processing', 'stage': 'ocr', 'progress': 50})}\n\n"
            await asyncio.sleep(_SSE_POLL_INTERVAL)

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/documents/{document_id}/file")
async def get_document_file(
    document_id: str,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    doc = await doc_repo.get_by_id(db, document_id)
    if not doc or doc.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail=error_response("not_found", "Document not found.", retryable=False),
        )
    storage = get_storage_backend()
    try:
        data = storage.get(doc.storage_key)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=error_response("not_found", "File not found in storage.", retryable=False),
        )
    _type_map = {"pdf": "application/pdf", "jpg": "image/jpeg", "png": "image/png", "csv": "text/csv"}
    return Response(content=data, media_type=_type_map.get(doc.file_type or "", "application/octet-stream"))


@router.get("/documents/{document_id}/summary")
async def get_document_summary(
    document_id: str,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    doc = await doc_repo.get_by_id(db, document_id)
    if not doc or doc.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail=error_response("not_found", "Document not found.", retryable=False),
        )
    return {
        "status": "ok",
        "data": {
            "document_id": doc.id,
            "original_filename": doc.original_filename,
            "file_type": doc.file_type,
            "file_size_bytes": doc.file_size_bytes,
            "status": doc.status,
            "extraction_method": doc.extraction_method,
            "extraction_confidence": doc.extraction_confidence,
            "extracted_fields": doc.extracted_fields,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
        },
    }


@router.delete("/documents/{document_id}")
async def archive_document(
    document_id: str,
    workspace_id: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    doc = await doc_repo.get_by_id(db, document_id)
    if not doc or doc.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail=error_response("not_found", "Document not found.", retryable=False),
        )
    await doc_repo.archive_by_id(db, document_id)
    return {"status": "ok", "data": {"document_id": document_id}}
