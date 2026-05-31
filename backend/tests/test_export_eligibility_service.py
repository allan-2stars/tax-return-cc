import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import EvidenceObligation, Workspace
from app.services.export_eligibility import ExportEligibilityService


@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def workspace(db_session):
    ws = Workspace(name="Export Eligibility WS", financial_year="2024-25", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest.mark.asyncio
async def test_export_eligibility_preview_blocks_on_required_missing_and_partial(db_session, workspace):
    db_session.add_all(
        [
            EvidenceObligation(
                workspace_id=workspace.id,
                financial_year="2024-25",
                source_type="profile",
                obligation_key="private_health_annual_statement",
                category="private_health",
                label="PHI",
                required_level="required",
                status="missing",
            ),
            EvidenceObligation(
                workspace_id=workspace.id,
                financial_year="2024-25",
                source_type="profile",
                obligation_key="wfh_evidence_log",
                category="wfh",
                label="WFH",
                required_level="required",
                status="partially_matched",
            ),
            EvidenceObligation(
                workspace_id=workspace.id,
                financial_year="2024-25",
                source_type="tax_event",
                obligation_key="bank_interest_statement",
                category="bank_interest",
                label="Bank Interest",
                required_level="recommended",
                status="missing",
            ),
        ]
    )
    await db_session.commit()

    preview = await ExportEligibilityService().build_preview(
        workspace_id=workspace.id,
        financial_year="2024-25",
        db=db_session,
    )
    assert preview.evidence_required_total == 2
    assert preview.evidence_total == 3
    assert preview.evidence_required_missing_total == 1
    assert preview.evidence_required_partial_total == 1
    assert preview.evidence_required_matched_total == 0
    assert preview.evidence_recommended_missing_total == 1
    assert preview.evidence_recommended_partial_total == 0
    assert preview.evidence_recommended_matched_total == 0
    assert preview.evidence_required_blocking_total == 2
    assert preview.would_block_export is True
    assert len(preview.blocking_evidence_obligations) == 2
    assert all("rule_version" in row for row in preview.blocking_evidence_obligations)


@pytest.mark.asyncio
async def test_export_eligibility_preview_not_blocking_when_required_matched(db_session, workspace):
    db_session.add(
        EvidenceObligation(
            workspace_id=workspace.id,
            financial_year="2024-25",
            source_type="profile",
            obligation_key="private_health_annual_statement",
            category="private_health",
            label="PHI",
            required_level="required",
            status="matched",
        )
    )
    await db_session.commit()

    preview = await ExportEligibilityService().build_preview(
        workspace_id=workspace.id,
        financial_year="2024-25",
        db=db_session,
    )
    assert preview.evidence_required_total == 1
    assert preview.evidence_total == 1
    assert preview.evidence_required_blocking_total == 0
    assert preview.evidence_required_missing_total == 0
    assert preview.evidence_required_partial_total == 0
    assert preview.evidence_required_matched_total == 1
    assert preview.would_block_export is False
