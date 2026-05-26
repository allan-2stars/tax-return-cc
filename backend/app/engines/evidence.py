import csv
import hashlib
import io
import uuid

import magic
import pdfplumber
import pytesseract
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.engines.sanitize import sanitize_for_ai
from app.errors import AppError, DuplicateDocumentError
from app.repositories import documents as doc_repo
from app.skills.registry import get_registry
from app.storage.base import StorageBackend

_ALLOWED_MIME: dict[str, str] = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "text/csv": "csv",
    "text/plain": "csv",
}


class EvidenceEngine:
    def __init__(
        self,
        db: AsyncSession,
        storage: StorageBackend,
        ai_adapter=None,
        readiness_engine=None,
        review_engine=None,
    ) -> None:
        self._db = db
        self.storage = storage
        self._ai_adapter = ai_adapter
        self._readiness_engine = readiness_engine
        self._review_engine = review_engine

    async def validate_and_create(
        self,
        workspace_id: str,
        financial_year: str,
        file_data: bytes,
        filename: str,
    ):
        # 1. Validate file size
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if len(file_data) > max_bytes:
            raise AppError(
                "file_too_large",
                f"This file is too large. Maximum size is {settings.MAX_FILE_SIZE_MB}MB.",
                retryable=False,
            )

        # 2. Validate file type via python-magic
        mime = magic.from_buffer(file_data, mime=True)
        if mime not in _ALLOWED_MIME:
            raise AppError(
                "unsupported_format",
                "This file format isn't supported.",
                retryable=False,
            )
        file_type = _ALLOWED_MIME[mime]

        # 3. SHA-256 hash
        sha256 = hashlib.sha256(file_data).hexdigest()

        # 4. Duplicate check — reject before any writes
        existing = await doc_repo.find_by_hash(self._db, workspace_id, sha256)
        if existing:
            raise DuplicateDocumentError(
                "duplicate_document",
                "You've already uploaded this document.",
                action="view_existing",
                retryable=False,
                existing_document_id=existing.id,
            )

        # 5. Save to storage (write-once)
        document_id = str(uuid.uuid4())
        orig_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else file_type
        storage_key = f"{workspace_id}/{document_id}/original.{orig_ext}"
        self.storage.save(storage_key, file_data)

        # 6. Create Document record
        doc = await doc_repo.create(
            self._db,
            id=document_id,
            workspace_id=workspace_id,
            financial_year=financial_year,
            original_filename=filename,
            storage_key=storage_key,
            file_type=file_type,
            file_size_bytes=len(file_data),
            sha256_hash=sha256,
            status="processing",
        )
        return doc

    async def attach_receipt(
        self,
        event_id: str,
        workspace_id: str,
        file_data: bytes,
        filename: str,
    ) -> object:
        """Save file + link its Document to an existing TaxEvent. No OCR/classification."""
        from app.repositories import events as events_repo

        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if len(file_data) > max_bytes:
            raise AppError(
                "file_too_large",
                f"This file is too large. Maximum size is {settings.MAX_FILE_SIZE_MB}MB.",
                retryable=False,
            )

        mime = magic.from_buffer(file_data, mime=True)
        if mime not in _ALLOWED_MIME:
            raise AppError(
                "unsupported_format",
                "This file format isn't supported.",
                retryable=False,
            )
        file_type = _ALLOWED_MIME[mime]

        sha256 = hashlib.sha256(file_data).hexdigest()

        document_id = str(uuid.uuid4())
        orig_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else file_type
        storage_key = f"{workspace_id}/{document_id}/original.{orig_ext}"
        self.storage.save(storage_key, file_data)

        doc = await doc_repo.create(
            self._db,
            id=document_id,
            workspace_id=workspace_id,
            financial_year="",
            original_filename=filename,
            storage_key=storage_key,
            file_type=file_type,
            file_size_bytes=len(file_data),
            sha256_hash=sha256,
            extraction_method="manual_attachment",
            status="ready",
        )

        await events_repo.attach_document(self._db, event_id, doc.id)

        return doc

    async def extract_and_finalize(self, document_id: str) -> None:
        from app.db.models import TaxEvent

        doc = await doc_repo.get_by_id(self._db, document_id)
        if not doc:
            return
        try:
            text, fields, method, confidence = self._extract(doc)
            sanitized, _ = sanitize_for_ai(text, None)
            await doc_repo.update_extraction(
                self._db, doc, sanitized, fields, method, confidence
            )

            # AI classification + skill extraction (only when adapter is wired in)
            if self._ai_adapter is not None:
                classification = await self._ai_adapter.classify(
                    text=sanitized or "", fields=fields, profile=None
                )
                # persist classification results onto the document record
                doc.document_type = classification.document_type
                doc.skill_id = classification.skill_id
                await self._db.commit()

                # classification.skill_id is a skill identifier, not a category.
                # get_owner expects a category, so use get_skill here.
                skill = get_registry().get_skill(classification.skill_id or "")
                if skill:
                    candidates = skill.extract_events(doc, classification)
                    new_events = []
                    for c in candidates:
                        ev = TaxEvent(
                            workspace_id=doc.workspace_id,
                            document_id=doc.id,
                            financial_year=doc.financial_year,
                            event_type=c.event_type,
                            category=c.category,
                            description=c.description,
                            amount=c.amount,
                            date=c.date,
                            source="document_extracted",
                            ai_reasoning=c.ai_reasoning,
                            confidence=c.confidence,
                            status="needs_user_review",
                            skill_id=classification.skill_id,
                            skill_version=skill.version if isinstance(getattr(skill, "version", None), str) else None,
                        )
                        self._db.add(ev)
                        new_events.append(ev)
                    await self._db.commit()
                    for ev in new_events:
                        await self._db.refresh(ev)
                    if self._review_engine is not None:
                        for ev in new_events:
                            await self._review_engine.create_review_item(ev, self._db)
                await doc_repo.update_status(self._db, document_id, "ready")
            else:
                await doc_repo.update_status(self._db, document_id, "ready")

            if self._readiness_engine is not None:
                await self._readiness_engine.mark_stale(doc.workspace_id, self._db)

        except Exception:
            await doc_repo.update_status(self._db, document_id, "failed")
            raise

    def _extract(self, doc) -> tuple[str, dict, str, float]:
        if doc.file_type == "csv":
            return self._extract_csv(doc)
        elif doc.file_type == "pdf":
            return self._extract_pdf(doc)
        else:
            return self._extract_image(doc)

    def _extract_pdf(self, doc) -> tuple[str, dict, str, float]:
        file_data = self.storage.get(doc.storage_key)
        with pdfplumber.open(io.BytesIO(file_data)) as pdf:
            pages_text = [p.extract_text() or "" for p in pdf.pages]
            text = "\n".join(pages_text).strip()

        if text:
            return text, {}, "pdfplumber", 0.95

        # Scanned PDF — render pages and run tesseract
        with pdfplumber.open(io.BytesIO(file_data)) as pdf:
            parts = []
            for page in pdf.pages:
                img = page.to_image(resolution=150).original
                parts.append(pytesseract.image_to_string(img))
            text = "\n".join(parts).strip()
        return text, {}, "tesseract", 0.80

    def _extract_image(self, doc) -> tuple[str, dict, str, float]:
        file_data = self.storage.get(doc.storage_key)
        img = Image.open(io.BytesIO(file_data))
        text = pytesseract.image_to_string(img)
        return text, {}, "tesseract", 0.80

    def _extract_csv(self, doc) -> tuple[str, dict, str, float]:
        from app.constants.csv_parsers import KNOWN_PARSERS

        file_data = self.storage.get(doc.storage_key)
        text = file_data.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        headers = list(reader.fieldnames or [])

        bank_name = None
        for parser in KNOWN_PARSERS:
            if all(col in headers for col in parser["required_columns"]):
                bank_name = parser["name"]
                break

        rows = [dict(row) for row in reader]
        fields = {
            "bank": bank_name,
            "rows": rows,
            "needs_column_mapping": bank_name is None,
        }
        return text, fields, "csv_parse", 1.0
