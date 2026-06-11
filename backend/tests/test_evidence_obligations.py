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
    event_type: str | None = None,
    amount: float = 100.0,
    metadata: dict | None = None,
):
    event = TaxEvent(
        workspace_id=workspace_id,
        financial_year=financial_year,
        event_type=event_type or ("deduction" if "deduction" in category or "expense" in category else "income"),
        category=category,
        description=f"Test {category}",
        amount=amount,
        status="needs_user_review",
        document_id=document_id,
        event_metadata=metadata or {},
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


@pytest.mark.asyncio
async def test_reconcile_creates_managed_fund_obligations(db_session, workspace):
    await _create_event(
        db_session,
        workspace.id,
        workspace.financial_year,
        category="managed_fund_distribution",
        event_type="investment_income",
        amount=1600.0,
        metadata={
            "investment_sub_type": "managed_fund",
            "fund_name": "Example Fund",
            "distribution_amount": 1600.0,
            "capital_gains_component": 450.0,
            "foreign_income_component": 120.0,
            "distribution_date": "2025-06-20",
        },
    )

    obligations = await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)

    by_key = {o.obligation_key: o for o in obligations}
    assert {
        "managed_fund_annual_tax_statement",
        "managed_fund_capital_gains_schedule",
        "managed_fund_foreign_income_support",
    }.issubset(by_key)
    assert by_key["managed_fund_annual_tax_statement"].required_level == "required"
    assert by_key["managed_fund_capital_gains_schedule"].required_level == "required"
    assert by_key["managed_fund_foreign_income_support"].required_level == "required"
    assert all(
        by_key[key].rule_version == CURRENT_EVIDENCE_RULE_VERSION
        for key in {
            "managed_fund_annual_tax_statement",
            "managed_fund_capital_gains_schedule",
            "managed_fund_foreign_income_support",
        }
    )


@pytest.mark.asyncio
async def test_reconcile_creates_share_obligations_and_deduplicates_broker_summary(db_session, workspace):
    await _create_event(
        db_session,
        workspace.id,
        workspace.financial_year,
        category="shares_acquisition",
        event_type="investment_position",
        amount=5020.0,
        metadata={
            "investment_sub_type": "shares",
            "transaction_type": "buy",
            "stock_code": "ABC",
            "units": 100,
            "price_per_unit": 50.0,
            "brokerage_fee": 20.0,
            "purchase_date": "2024-09-01",
        },
    )
    await _create_event(
        db_session,
        workspace.id,
        workspace.financial_year,
        category="dividend",
        event_type="investment_income",
        amount=180.0,
        metadata={
            "investment_sub_type": "shares",
            "transaction_type": "dividend",
            "stock_code": "ABC",
            "dividend_amount": 180.0,
            "franking_credits": 77.0,
            "payment_date": "2025-03-12",
        },
    )
    await _create_event(
        db_session,
        workspace.id,
        workspace.financial_year,
        category="capital_gain",
        event_type="capital",
        amount=700.0,
        metadata={
            "investment_sub_type": "shares",
            "transaction_type": "sell",
            "stock_code": "ABC",
            "purchase_date": "2024-09-01",
            "sale_date": "2025-04-10",
            "purchase_price": 5020.0,
            "sale_price": 5720.0,
            "amount_units": 100,
        },
    )

    obligations = await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)

    by_key = {o.obligation_key: o for o in obligations}
    assert {
        "share_buy_contract_note",
        "share_sell_contract_note",
        "share_dividend_statement",
        "share_annual_broker_summary",
    }.issubset(by_key)
    assert by_key["share_annual_broker_summary"].required_level == "recommended"

    count = (
        await db_session.execute(
            select(EvidenceObligation).where(
                EvidenceObligation.workspace_id == workspace.id,
                EvidenceObligation.obligation_key == "share_annual_broker_summary",
            )
        )
    ).scalars().all()
    assert len(count) == 1


@pytest.mark.asyncio
async def test_reconcile_creates_share_sell_contract_from_asset_class_compatibility(db_session, workspace):
    await _create_event(
        db_session,
        workspace.id,
        workspace.financial_year,
        category="capital_loss",
        event_type="capital",
        amount=300.0,
        metadata={
            "asset_class": "shares",
            "stock_code": "ABC",
            "purchase_date": "2024-09-01",
            "disposal_date": "2025-04-10",
            "cost_base": 1200.0,
            "capital_proceeds": 900.0,
        },
    )

    obligations = await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)
    assert any(o.obligation_key == "share_sell_contract_note" for o in obligations)


@pytest.mark.asyncio
async def test_reconcile_creates_crypto_obligations_and_deduplicates_wallet_export(db_session, workspace):
    await _create_event(
        db_session,
        workspace.id,
        workspace.financial_year,
        category="crypto_acquisition",
        event_type="investment_position",
        amount=2000.0,
        metadata={
            "investment_sub_type": "crypto",
            "transaction_type": "buy",
            "coin": "BTC",
            "amount_units": 0.05,
            "purchase_price": 2000.0,
            "transaction_fee": 0.0,
            "purchase_date": "2024-08-01",
        },
    )
    await _create_event(
        db_session,
        workspace.id,
        workspace.financial_year,
        category="capital_loss",
        event_type="capital",
        amount=300.0,
        metadata={
            "investment_sub_type": "crypto",
            "transaction_type": "sell",
            "coin": "BTC",
            "amount_units": 0.05,
            "purchase_price": 1200.0,
            "sale_price": 900.0,
            "transaction_fee": 0.0,
            "purchase_date": "2024-08-01",
            "sale_date": "2025-02-01",
        },
    )
    await _create_event(
        db_session,
        workspace.id,
        workspace.financial_year,
        category="crypto",
        event_type="investment_income",
        amount=80.0,
        metadata={
            "investment_sub_type": "crypto",
            "transaction_type": "staking",
            "coin": "ETH",
            "income_amount": 80.0,
            "staking_income": 80.0,
            "income_date": "2025-01-15",
        },
    )

    obligations = await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)

    by_key = {o.obligation_key: o for o in obligations}
    assert {
        "crypto_exchange_transaction_export",
        "crypto_disposal_supporting_records",
        "crypto_staking_income_statement",
        "crypto_wallet_activity_export",
    }.issubset(by_key)
    assert by_key["crypto_wallet_activity_export"].required_level == "recommended"

    count = (
        await db_session.execute(
            select(EvidenceObligation).where(
                EvidenceObligation.workspace_id == workspace.id,
                EvidenceObligation.obligation_key == "crypto_wallet_activity_export",
            )
        )
    ).scalars().all()
    assert len(count) == 1


@pytest.mark.asyncio
async def test_reconcile_creates_crypto_disposal_obligation_from_asset_class_compatibility(db_session, workspace):
    await _create_event(
        db_session,
        workspace.id,
        workspace.financial_year,
        category="capital_gain",
        event_type="capital",
        amount=700.0,
        metadata={
            "asset_class": "crypto",
            "coin": "BTC",
            "purchase_date": "2024-08-01",
            "disposal_date": "2025-02-01",
            "cost_base": 1200.0,
            "capital_proceeds": 1900.0,
        },
    )
    obligations = await reconcile_evidence_obligations(workspace.id, workspace.financial_year, db_session)
    assert any(o.obligation_key == "crypto_disposal_supporting_records" for o in obligations)
