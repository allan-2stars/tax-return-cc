import csv
import hashlib
import io
import re
import uuid

import magic
import pdfplumber
import pytesseract
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.errors import AppError, DuplicateDocumentError
from app.repositories import documents as doc_repo
from app.storage.base import StorageBackend

_ALLOWED_MIME: dict[str, str] = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "text/csv": "csv",
    "text/plain": "csv",
}

# Sanitization patterns — order matters (TFN first, then shorter patterns)
_TFN_RE = re.compile(r"\b\d{3}-\d{3}-\d{3}\b")
_BSB_RE = re.compile(r"\b\d{6}\b")
_ACCT_RE = re.compile(r"\b\d{8,16}\b")


def _sanitize(text: str) -> str:
    text = _TFN_RE.sub("[TFN]", text)
    text = _BSB_RE.sub("[BSB]", text)
    text = _ACCT_RE.sub("[ACCT]", text)
    return text


class EvidenceEngine:
    def __init__(self, db: AsyncSession, storage: StorageBackend) -> None:
        self._db = db
        self.storage = storage

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

    async def extract_and_finalize(self, document_id: str) -> None:
        doc = await doc_repo.get_by_id(self._db, document_id)
        if not doc:
            return
        try:
            text, fields, method, confidence = self._extract(doc)
            sanitized = _sanitize(text) if text else None
            await doc_repo.update_extraction(
                self._db, doc, sanitized, fields, method, confidence
            )
            await doc_repo.update_status(self._db, document_id, "ready")
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
