import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jinja2
import pyzipper
from weasyprint import HTML

from app.config import settings
from app.repositories import exports as exports_repo
from app.repositories import jobs as jobs_repo

_DISCLAIMER_TEXT = (
    "This tool helps organise your tax information and prepare a review package. "
    "It does not provide final tax advice and does not replace review by "
    "a registered tax agent."
)

_SCHEMA_VERSION = "1.0"

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "export"


@dataclass
class ExportEligibility:
    can_export: bool
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── background task ───────────────────────────────────────────────────────────

async def _run_export(
    export_id: str,
    workspace_id: str,
    password: str,
    export_path: str,
    storage,
    job_id: str,
) -> None:
    from app.db.base import AsyncSessionLocal
    from app.repositories import audit as audit_repo
    from app.repositories import documents as doc_repo
    from app.repositories import events as events_repo
    from app.repositories import readiness as readiness_repo
    from app.repositories import review as review_repo
    from app.db.models import Workspace

    async with AsyncSessionLocal() as db:
        try:
            await jobs_repo.update_status(db, job_id, "running")

            ws = await db.get(Workspace, workspace_id)
            if not ws:
                raise ValueError("Workspace not found.")
            fy = ws.financial_year

            # Snapshot readiness at export time (ARCHITECTURE.md §15 addition)
            readiness = await readiness_repo.get_score(db, workspace_id)
            readiness_pct = readiness.percentage if readiness else 0.0

            events = await events_repo.get_by_workspace(db, workspace_id)
            confirmed = [e for e in events if e.status == "confirmed"]
            income_events = [e for e in confirmed if e.event_type == "income"]
            deduction_events = [
                e for e in confirmed if e.event_type in ("deduction", "wfh")
            ]

            review_items = await review_repo.get_queue(db, workspace_id)
            agent_items = [i for i in review_items if i.status == "needs_agent_review"]
            pending_items = [
                i for i in review_items if i.status != "confirmed"
            ]
            documents = await doc_repo.get_ready_docs(db, workspace_id)
            audit_logs = await audit_repo.get_by_workspace(db, workspace_id)

            generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

            # Render PDFs via Jinja2 + WeasyPrint
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
                autoescape=True,
            )

            cover_html = env.get_template("cover.html").render(
                fy=fy,
                workspace_id=workspace_id,
                generated_at=generated_at,
                readiness_pct=readiness_pct,
                income_events=income_events,
                deduction_events=deduction_events,
                agent_items=agent_items,
            )
            summary_html = env.get_template("summary.html").render(
                fy=fy,
                generated_at=generated_at,
                review_items=review_items,
                confirmed_count=len([i for i in review_items if i.status == "confirmed"]),
                review_count=len(pending_items),
                agent_count=len(agent_items),
            )
            missing_html = env.get_template("missing.html").render(
                fy=fy,
                generated_at=generated_at,
                missing_items=[],
            )

            cover_pdf = HTML(string=cover_html).write_pdf()
            summary_pdf = HTML(string=summary_html).write_pdf()
            missing_pdf = HTML(string=missing_html).write_pdf()

            # Build zip
            zip_dir = Path(export_path) / workspace_id
            zip_dir.mkdir(parents=True, exist_ok=True)
            zip_path = zip_dir / f"{export_id}.zip"
            storage_key = f"{workspace_id}/{export_id}.zip"

            with pyzipper.AESZipFile(
                str(zip_path),
                "w",
                compression=pyzipper.ZIP_DEFLATED,
                encryption=pyzipper.WZ_AES,
            ) as zf:
                zf.setpassword(password.encode())

                zf.writestr("00-COVER.pdf", cover_pdf)
                zf.writestr("01-TAX-EVENTS.json", json.dumps(
                    [_event_dict(e) for e in confirmed], default=str
                ))
                zf.writestr("02-REVIEW-SUMMARY.pdf", summary_pdf)
                zf.writestr("03-MISSING-ITEMS.pdf", missing_pdf)
                zf.writestr("04-AI-REASONING.json", json.dumps(
                    [{"event_id": e.id, "reasoning": e.ai_reasoning} for e in confirmed],
                    default=str,
                ))
                zf.writestr("05-AUDIT-LOG.json", json.dumps(
                    [_audit_dict(a) for a in audit_logs], default=str
                ))
                zf.writestr("06-SCHEMA-VERSION.txt", _SCHEMA_VERSION)
                zf.writestr("07-DISCLAIMER.txt", _DISCLAIMER_TEXT)

                # Evidence files
                evidence_manifest = []
                for doc in documents:
                    if storage is not None:
                        try:
                            file_bytes = storage.get(doc.storage_key)
                            archive_name = f"evidence/{doc.id}_{doc.original_filename}"
                            zf.writestr(archive_name, file_bytes)
                            evidence_manifest.append({
                                "document_id": doc.id,
                                "filename": doc.original_filename,
                                "file_type": doc.file_type,
                                "archive_name": archive_name,
                            })
                        except Exception:
                            pass

                zf.writestr("evidence/manifest.json", json.dumps(evidence_manifest))

            file_size = zip_path.stat().st_size if zip_path.exists() else 0

            await exports_repo.update_status(
                db, export_id, "ready",
                storage_key=storage_key,
                file_size_bytes=file_size,
            )
            await jobs_repo.update_status(
                db, job_id, "complete", result={"export_id": export_id}
            )

        except Exception as exc:
            try:
                await exports_repo.update_status(db, export_id, "failed")
                await jobs_repo.update_status(db, job_id, "failed", error=str(exc))
            except Exception:
                pass
            raise


# ── helpers ───────────────────────────────────────────────────────────────────

def _event_dict(ev) -> dict:
    return {
        "id": ev.id,
        "event_type": ev.event_type,
        "category": ev.category,
        "description": ev.description,
        "amount": ev.amount,
        "date": ev.date,
        "status": ev.status,
        "ai_reasoning": ev.ai_reasoning,
        "user_note": ev.user_note,
    }


def _audit_dict(a) -> dict:
    return {
        "id": a.id,
        "action": a.action,
        "actor": a.actor,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "note": a.note,
    }


# ── ExportEngine ──────────────────────────────────────────────────────────────

class ExportEngine:
    def __init__(
        self,
        export_path: str | None = None,
        storage=None,
    ) -> None:
        self._export_path = export_path or settings.EXPORT_PATH
        self._storage = storage

    # ── check eligibility ─────────────────────────────────────────────────────

    async def check_eligibility(self, workspace_id: str, db) -> ExportEligibility:
        from app.repositories import documents as doc_repo
        from app.repositories import events as events_repo
        from app.repositories import review as review_repo

        blocking: list[str] = []
        warnings: list[str] = []

        # Check 1: interview must be complete
        from sqlalchemy import select as _select
        from app.db.models import InterviewSession as _SessionModel
        _sess_result = await db.execute(
            _select(_SessionModel).where(
                _SessionModel.workspace_id == workspace_id,
                _SessionModel.state.in_(["awaiting_evidence", "complete"]),
            ).limit(1)
        )
        session = _sess_result.scalar_one_or_none()
        if session is None:
            blocking.append(
                "Interview must be complete before exporting. "
                "Please finish the interview first."
            )

        # Check 2: at least one confirmed event
        events = await events_repo.get_by_workspace(db, workspace_id)
        if not any(e.status == "confirmed" for e in events):
            blocking.append(
                "No confirmed events found. "
                "Please confirm at least one item in the review queue."
            )

        # Check 3: no documents still processing
        all_docs = await doc_repo.get_ready_docs(db, workspace_id)
        # Also check processing docs (get_ready_docs excludes them, query separately)
        from sqlalchemy import select
        from app.db.models import Document as DocModel
        processing_result = await db.execute(
            select(DocModel).where(
                DocModel.workspace_id == workspace_id,
                DocModel.status == "processing",
            )
        )
        processing_docs = processing_result.scalars().all()
        if processing_docs:
            blocking.append(
                f"{len(processing_docs)} document(s) are still processing. "
                "Please wait for processing to complete."
            )

        # Soft warnings
        review_items = await review_repo.get_queue(db, workspace_id)
        pending = [i for i in review_items if i.status not in ("confirmed",)]
        if pending:
            warnings.append(
                f"{len(pending)} review item(s) have not been confirmed. "
                "Consider reviewing them before exporting."
            )

        agent_items = [i for i in review_items if i.status == "needs_agent_review"]
        if agent_items:
            warnings.append(
                f"{len(agent_items)} item(s) require agent review. "
                "Your tax agent will need to assess these."
            )

        return ExportEligibility(
            can_export=len(blocking) == 0,
            blocking_reasons=blocking,
            warnings=warnings,
        )

    # ── generate ──────────────────────────────────────────────────────────────

    async def generate(
        self, workspace_id: str, password: str, db
    ) -> object:
        from app.repositories import events as events_repo
        from app.repositories import readiness as readiness_repo
        from app.repositories import review as review_repo
        from app.db.models import Workspace

        ws = await db.get(Workspace, workspace_id)
        if not ws:
            raise ValueError("Workspace not found.")
        fy = ws.financial_year

        events = await events_repo.get_by_workspace(db, workspace_id)
        confirmed = [e for e in events if e.status == "confirmed"]
        review_items = await review_repo.get_queue(db, workspace_id)
        pending = [i for i in review_items if i.status != "confirmed"]
        agent = [i for i in review_items if i.status == "needs_agent_review"]

        readiness = await readiness_repo.get_score(db, workspace_id)
        readiness_pct = readiness.percentage if readiness else 0.0

        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.EXPORT_RETENTION_HOURS
        )

        job = await jobs_repo.create_job(
            db, workspace_id, "export_generate",
            payload={"workspace_id": workspace_id, "fy": fy},
        )

        record = await exports_repo.create(
            db,
            workspace_id=workspace_id,
            financial_year=fy,
            readiness_pct=readiness_pct,
            confirmed_count=len(confirmed),
            review_count=len(pending),
            agent_count=len(agent),
            expires_at=expires_at,
        )

        asyncio.create_task(
            _run_export(
                export_id=record.id,
                workspace_id=workspace_id,
                password=password,
                export_path=self._export_path,
                storage=self._storage,
                job_id=job.id,
            )
        )

        return record

    # ── get download ──────────────────────────────────────────────────────────

    async def get_download(
        self, export_id: str, workspace_id: str, db
    ) -> tuple[bytes, str]:
        record = await exports_repo.get_by_id(db, export_id)
        if record is None or record.workspace_id != workspace_id:
            raise ValueError(f"Export {export_id!r} not found")
        if record.status != "ready":
            raise ValueError(
                f"Export is not ready (status={record.status!r}). "
                "Check /export/{id}/status and try again."
            )
        zip_path = Path(self._export_path) / record.storage_key
        if not zip_path.exists():
            raise ValueError("Export file has been deleted or expired")
        data = zip_path.read_bytes()
        fy = record.financial_year.replace("/", "-")
        filename = f"review-package-{fy}-{workspace_id[:8]}.zip"
        return data, filename

    # ── get history ───────────────────────────────────────────────────────────

    async def get_history(self, workspace_id: str, db) -> list:
        return await exports_repo.get_history(db, workspace_id)

    # ── cleanup expired ───────────────────────────────────────────────────────

    async def cleanup_expired(self, db) -> int:
        expired_records = await exports_repo.get_expired(
            db, settings.EXPORT_RETENTION_HOURS
        )
        count = 0
        for record in expired_records:
            if record.storage_key:
                zip_path = Path(self._export_path) / record.storage_key
                if zip_path.exists():
                    zip_path.unlink()
            await exports_repo.update_status(db, record.id, "expired")
            count += 1
        return count
