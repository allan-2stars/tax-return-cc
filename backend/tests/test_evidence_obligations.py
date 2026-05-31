import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import Document, EvidenceMatch, EvidenceObligation, TaxEvent, TaxProfile, Workspace
from app.engines.evidence_obligations import reconcile_evidence_obligations
from app.services.evidence_rules import CURRENT_EVIDENCE_RULE_VERSION


@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def workspace(db_session):
    ws = Workspace(name="Evidence Obligations WS", financial_year="2024-25", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


async def _create_profile(
    db_session: AsyncSession,
    workspace_id: str,
    financial_year: str,
    *,
    has_private_health: bool = False,
    has_wfh: bool = False,
):
    profile = TaxProfile(
        workspace_id=workspace_id,
        financial_year=financial_year,
        has_private_health=has_private_health,
        has_wfh=has_wfh,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


async def _create_event(
    db_session: AsyncSession,
    workspace_id: str,
    financial_year: str,
    *,
    category: str,
    document_id: str | None = None,
):
    event = TaxEvent(
        workspace_id=workspace_id,
        financial_year=financial_year,
        event_type="deduction" if "deduction" in category or "expense" in category else "income",
        category=category,
        description=f"Test {category}",
        amount=100.0,
        status="needs_user_review",
        document_id=document_id,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


async def _create_document(
    db_session: AsyncSession,
    workspace_id: str,
    financial_year: str,
    *,
    document_type: str,
    original_filename: str = "test.pdf",
):
    doc = Document(
        workspace_id=workspace_id,
        financial_year=financial_year,
        original_filename=original_filename,
        storage_key=f"ws/{workspace_id}/{original_filename}",
        file_type="application/pdf",
        file_size_bytes=123,
        sha256_hash=f"{original_filename:0<64}"[:64],
        document_type=document_type,
        status="ready",
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest.mark.asyncio
async def test_reconcile_creates_obligations_from_profile_and_events(db_session, workspace):
    await _create_profile(
        db_session,
        workspace.id,
        workspace.financial_year,
        has_private_health=True,
        has_wfh=True,
    )
    await _create_event(
        db_session,
        workspace.id,
        workspace.financial_year,
        category="donation",
    )
    await _create_event(
        db_session,
        workspace.id,
        workspace.financial_year,
        category="work_expense",
    )
    await _create_event(
        db_session,
        workspace.id,
        workspace.financial_year,
        category="bank_interest",
    )

    obligations = await reconcile_evidence_obligations(
        workspace.id,
        workspace.financial_year,
        db_session,
    )

    keys = {o.obligation_key for o in obligations}
    assert keys == {
        "private_health_annual_statement",
        "wfh_evidence_log",
        "donation_receipt",
        "work_expense_receipt",
        "bank_interest_statement",
    }

    by_key = {o.obligation_key: o for o in obligations}
    assert all(o.rule_version == CURRENT_EVIDENCE_RULE_VERSION for o in obligations)
    assert by_key["private_health_annual_statement"].source_type == "profile"
    assert by_key["wfh_evidence_log"].source_type == "profile"
    assert by_key["donation_receipt"].source_type == "tax_event"
    assert by_key["work_expense_receipt"].source_type == "tax_event"
    assert by_key["bank_interest_statement"].required_level == "recommended"


@pytest.mark.asyncio
async def test_reconcile_is_idempotent_and_status_stable(db_session, workspace):
    await _create_profile(
        db_session,
        workspace.id,
        workspace.financial_year,
        has_private_health=True,
        has_wfh=False,
    )
    doc = await _create_document(
        db_session,
        workspace.id,
        workspace.financial_year,
        document_type="private_health_statement",
        original_filename="phi.pdf",
    )

    first = await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)
    second = await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)

    assert {o.id for o in first} == {o.id for o in second}

    result = await db_session.execute(
        select(EvidenceObligation).where(
            EvidenceObligation.workspace_id == workspace.id,
            EvidenceObligation.obligation_key == "private_health_annual_statement",
        )
    )
    phi_obligation = result.scalar_one()
    assert phi_obligation.status == "partially_matched"

    matches_result = await db_session.execute(
        select(EvidenceMatch).where(
            EvidenceMatch.workspace_id == workspace.id,
            EvidenceMatch.obligation_id == phi_obligation.id,
        )
    )
    matches = matches_result.scalars().all()
    assert len(matches) == 1
    assert matches[0].document_id == doc.id
    assert matches[0].status == "candidate"


@pytest.mark.asyncio
async def test_reconcile_creates_tax_event_match_link(db_session, workspace):
    await _create_profile(
        db_session,
        workspace.id,
        workspace.financial_year,
        has_private_health=False,
        has_wfh=False,
    )
    event = await _create_event(
        db_session,
        workspace.id,
        workspace.financial_year,
        category="bank_interest",
    )

    await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)

    obligation_result = await db_session.execute(
        select(EvidenceObligation).where(
            EvidenceObligation.workspace_id == workspace.id,
            EvidenceObligation.obligation_key == "bank_interest_statement",
        )
    )
    obligation = obligation_result.scalar_one()

    match_result = await db_session.execute(
        select(EvidenceMatch).where(
            EvidenceMatch.workspace_id == workspace.id,
            EvidenceMatch.obligation_id == obligation.id,
            EvidenceMatch.tax_event_id == event.id,
        )
    )
    match = match_result.scalar_one_or_none()
    assert match is not None
    assert match.match_type == "tax_event"
    assert match.status == "candidate"


@pytest.mark.asyncio
async def test_reconcile_document_match_creates_candidate_for_wfh(db_session, workspace):
    await _create_profile(
        db_session,
        workspace.id,
        workspace.financial_year,
        has_wfh=True,
    )
    doc = await _create_document(
        db_session,
        workspace.id,
        workspace.financial_year,
        document_type="timesheet",
        original_filename="timesheet.pdf",
    )

    obligations = await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)
    wfh = next(o for o in obligations if o.obligation_key == "wfh_evidence_log")
    assert wfh.status == "partially_matched"

    match_result = await db_session.execute(
        select(EvidenceMatch).where(
            EvidenceMatch.workspace_id == workspace.id,
            EvidenceMatch.obligation_id == wfh.id,
            EvidenceMatch.document_id == doc.id,
        )
    )
    match = match_result.scalar_one_or_none()
    assert match is not None
    assert match.status == "candidate"


@pytest.mark.asyncio
async def test_reconcile_preserves_accepted_match_and_sets_matched(db_session, workspace):
    await _create_profile(
        db_session,
        workspace.id,
        workspace.financial_year,
        has_private_health=True,
    )
    doc = await _create_document(
        db_session,
        workspace.id,
        workspace.financial_year,
        document_type="private_health_statement",
        original_filename="phi-accepted.pdf",
    )
    obligations = await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)
    phi = next(o for o in obligations if o.obligation_key == "private_health_annual_statement")

    existing = (
        await db_session.execute(
            select(EvidenceMatch).where(
                EvidenceMatch.workspace_id == workspace.id,
                EvidenceMatch.obligation_id == phi.id,
                EvidenceMatch.document_id == doc.id,
            )
        )
    ).scalar_one()
    existing.status = "accepted"
    await db_session.commit()

    await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)
    await db_session.refresh(phi)
    assert phi.status == "matched"

    matches = (
        await db_session.execute(
            select(EvidenceMatch).where(
                EvidenceMatch.workspace_id == workspace.id,
                EvidenceMatch.obligation_id == phi.id,
                EvidenceMatch.document_id == doc.id,
            )
        )
    ).scalars().all()
    assert len(matches) == 1
    assert matches[0].status == "accepted"


@pytest.mark.asyncio
async def test_reconcile_preserves_rejected_and_does_not_recreate_candidate(db_session, workspace):
    await _create_profile(
        db_session,
        workspace.id,
        workspace.financial_year,
        has_private_health=True,
    )
    doc = await _create_document(
        db_session,
        workspace.id,
        workspace.financial_year,
        document_type="private_health_statement",
        original_filename="phi-rejected.pdf",
    )
    obligations = await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)
    phi = next(o for o in obligations if o.obligation_key == "private_health_annual_statement")

    existing = (
        await db_session.execute(
            select(EvidenceMatch).where(
                EvidenceMatch.workspace_id == workspace.id,
                EvidenceMatch.obligation_id == phi.id,
                EvidenceMatch.document_id == doc.id,
            )
        )
    ).scalar_one()
    existing.status = "rejected"
    await db_session.commit()

    await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)

    matches = (
        await db_session.execute(
            select(EvidenceMatch).where(
                EvidenceMatch.workspace_id == workspace.id,
                EvidenceMatch.obligation_id == phi.id,
                EvidenceMatch.document_id == doc.id,
            )
        )
    ).scalars().all()
    assert len(matches) == 1
    assert matches[0].status == "rejected"


@pytest.mark.asyncio
async def test_reconcile_workspace_and_financial_year_scoping(db_session):
    ws_a = Workspace(name="WS-A", financial_year="2024-25", status="active")
    ws_b = Workspace(name="WS-B", financial_year="2024-25", status="active")
    db_session.add_all([ws_a, ws_b])
    await db_session.commit()
    await db_session.refresh(ws_a)
    await db_session.refresh(ws_b)

    await _create_profile(db_session, ws_a.id, "2024-25", has_private_health=True)
    await _create_profile(db_session, ws_b.id, "2024-25", has_private_health=True)
    await _create_document(db_session, ws_a.id, "2024-25", document_type="private_health_statement", original_filename="a.pdf")
    await _create_document(db_session, ws_b.id, "2024-25", document_type="private_health_statement", original_filename="b.pdf")
    await _create_document(db_session, ws_a.id, "2023-24", document_type="private_health_statement", original_filename="old-fy.pdf")

    await reconcile_evidence_obligations(ws_a.id, "2024-25", db_session)

    obligations = (
        await db_session.execute(
            select(EvidenceObligation).where(EvidenceObligation.workspace_id == ws_a.id)
        )
    ).scalars().all()
    assert len(obligations) == 1
    phi = obligations[0]

    matches = (
        await db_session.execute(
            select(EvidenceMatch).where(EvidenceMatch.obligation_id == phi.id)
        )
    ).scalars().all()
    assert len(matches) == 1
    assert matches[0].workspace_id == ws_a.id


@pytest.mark.asyncio
async def test_reconcile_legacy_null_rule_version_remains_valid(db_session, workspace):
    await _create_profile(
        db_session,
        workspace.id,
        workspace.financial_year,
        has_private_health=True,
    )
    legacy = EvidenceObligation(
        workspace_id=workspace.id,
        financial_year=workspace.financial_year,
        source_type="profile",
        obligation_key="private_health_annual_statement",
        category="private_health",
        label="Private Health Insurance Annual Statement",
        description="Provide your annual private health insurance statement.",
        required_level="required",
        status="missing",
        reason="Legacy obligation",
        rule_version=None,
    )
    db_session.add(legacy)
    await db_session.commit()
    legacy_id = legacy.id

    obligations = await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)
    phi = next(o for o in obligations if o.obligation_key == "private_health_annual_statement")
    assert phi.id == legacy_id
    assert phi.rule_version == CURRENT_EVIDENCE_RULE_VERSION


@pytest.mark.asyncio
async def test_reconcile_document_archive_clears_candidates_but_preserves_manual_decisions(db_session, workspace):
    await _create_profile(
        db_session,
        workspace.id,
        workspace.financial_year,
        has_private_health=True,
    )
    doc = await _create_document(
        db_session,
        workspace.id,
        workspace.financial_year,
        document_type="private_health_statement",
        original_filename="phi-archive-test.pdf",
    )
    obligations = await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)
    phi = next(o for o in obligations if o.obligation_key == "private_health_annual_statement")
    existing = (
        await db_session.execute(
            select(EvidenceMatch).where(
                EvidenceMatch.workspace_id == workspace.id,
                EvidenceMatch.obligation_id == phi.id,
                EvidenceMatch.document_id == doc.id,
            )
        )
    ).scalar_one()
    existing.status = "rejected"
    await db_session.commit()

    doc.archived = True
    await db_session.commit()

    await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)

    matches = (
        await db_session.execute(
            select(EvidenceMatch).where(
                EvidenceMatch.workspace_id == workspace.id,
                EvidenceMatch.obligation_id == phi.id,
                EvidenceMatch.document_id == doc.id,
            )
        )
    ).scalars().all()
    assert len(matches) == 1
    assert matches[0].status == "rejected"


@pytest.mark.asyncio
async def test_reconcile_creates_wfh_obligation_from_wfh_deduction_event_without_profile_flag(db_session, workspace):
    await _create_profile(
        db_session,
        workspace.id,
        workspace.financial_year,
        has_private_health=False,
        has_wfh=False,
    )
    await _create_event(
        db_session,
        workspace.id,
        workspace.financial_year,
        category="wfh_deduction",
    )

    obligations = await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)
    wfh = next((o for o in obligations if o.obligation_key == "wfh_evidence_log"), None)
    assert wfh is not None
    assert wfh.source_type == "tax_event"
