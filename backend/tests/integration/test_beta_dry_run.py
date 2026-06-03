from __future__ import annotations

from dataclasses import dataclass, field

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.routes.readiness import _build_readiness_2_0
from app.db.models import (
    Document,
    EvidenceMatch,
    EvidenceObligation,
    InterviewSession,
    ReviewItem,
    TaxEvent,
    TaxProfile,
    Workspace,
)
from app.engines.evidence_obligations import reconcile_evidence_obligations
from app.engines.export import ExportEngine
from app.engines.review import ReviewEngine
from app.services.explanations import (
    build_evidence_obligation_explanation,
    build_tax_item_explanation,
)
from app.services.export_eligibility import ExportEligibilityService


FY = "2024-25"


@dataclass(frozen=True)
class DocumentSeed:
    document_type: str
    filename: str


@dataclass(frozen=True)
class EventSeed:
    category: str
    event_type: str
    amount: float
    description: str
    date: str = "2025-06-01"
    status: str = "confirmed"
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class BetaScenario:
    scenario_id: str
    title: str
    profile: dict
    answers: dict
    documents: tuple[DocumentSeed, ...]
    events: tuple[EventSeed, ...]
    expected_obligation_keys: set[str]
    expected_event_categories: set[str]
    expected_review_categories: set[str]
    expected_journey_state: str
    expected_review_state: str
    expected_evidence_state: str
    expected_export_can_export: bool
    expected_evidence_would_block_export: bool
    expected_explanation_categories: set[str]
    known_gap_obligation_keys: set[str] = field(default_factory=set)


SCENARIOS = [
    BetaScenario(
        scenario_id="BETA-001",
        title="PAYG only with bank interest",
        profile={"employment_type": "employee"},
        answers={"employment_type": "employee", "has_wfh": "no", "has_investments": "no"},
        documents=(
            DocumentSeed("income_statement", "income-statement.pdf"),
            DocumentSeed("bank_interest_statement", "bank-interest.pdf"),
        ),
        events=(
            EventSeed("payg_income", "income", 84000.0, "PAYG income"),
            EventSeed(
                "bank_interest",
                "income",
                120.0,
                "Bank interest",
                metadata={
                    "schema_version": "2026.1",
                    "bank_name": "Example Bank",
                    "account_type": "savings",
                    "interest_amount": 120.0,
                    "period_start": "2024-07-01",
                    "period_end": "2025-06-30",
                },
            ),
        ),
        expected_obligation_keys={"bank_interest_statement"},
        expected_event_categories={"payg_income", "bank_interest"},
        expected_review_categories={"payg_income", "bank_interest"},
        expected_journey_state="ready",
        expected_review_state="ready",
        expected_evidence_state="ready",
        expected_export_can_export=True,
        expected_evidence_would_block_export=False,
        expected_explanation_categories={"bank_interest"},
    ),
    BetaScenario(
        scenario_id="BETA-002",
        title="PAYG plus WFH with evidence supplied",
        profile={"employment_type": "employee", "has_wfh": True},
        answers={"employment_type": "employee", "has_wfh": "yes_regular", "wfh_days": 3, "wfh_method": "fixed_rate"},
        documents=(
            DocumentSeed("income_statement", "income-statement.pdf"),
            DocumentSeed("timesheet", "wfh-timesheet.pdf"),
        ),
        events=(
            EventSeed("payg_income", "income", 84000.0, "PAYG income"),
            EventSeed(
                "wfh_deduction",
                "deduction",
                750.0,
                "WFH fixed-rate claim",
                metadata={
                    "schema_version": "2026.1",
                    "method": "fixed_rate",
                    "financial_year": FY,
                    "hours": 720,
                    "evidence_available": True,
                },
            ),
        ),
        expected_obligation_keys={"wfh_evidence_log"},
        expected_event_categories={"payg_income", "wfh_deduction"},
        expected_review_categories={"payg_income", "wfh_deduction"},
        expected_journey_state="ready",
        expected_review_state="ready",
        expected_evidence_state="blocked",
        expected_export_can_export=True,
        expected_evidence_would_block_export=True,
        expected_explanation_categories={"wfh_deduction"},
    ),
    BetaScenario(
        scenario_id="BETA-003",
        title="PAYG plus WFH with evidence missing",
        profile={"employment_type": "employee", "has_wfh": True},
        answers={"employment_type": "employee", "has_wfh": "yes_regular", "wfh_days": 3, "wfh_method": "fixed_rate"},
        documents=(
            DocumentSeed("income_statement", "income-statement.pdf"),
        ),
        events=(
            EventSeed("payg_income", "income", 84000.0, "PAYG income"),
            EventSeed(
                "wfh_deduction",
                "deduction",
                750.0,
                "WFH fixed-rate claim",
                metadata={
                    "schema_version": "2026.1",
                    "method": "fixed_rate",
                    "financial_year": FY,
                    "hours": 720,
                    "evidence_available": False,
                },
            ),
        ),
        expected_obligation_keys={"wfh_evidence_log"},
        expected_event_categories={"payg_income", "wfh_deduction"},
        expected_review_categories={"payg_income", "wfh_deduction"},
        expected_journey_state="ready",
        expected_review_state="ready",
        expected_evidence_state="blocked",
        expected_export_can_export=True,
        expected_evidence_would_block_export=True,
        expected_explanation_categories={"wfh_deduction"},
    ),
    BetaScenario(
        scenario_id="BETA-004",
        title="PAYG plus donations",
        profile={"employment_type": "employee"},
        answers={"employment_type": "employee", "has_donations": "yes"},
        documents=(
            DocumentSeed("income_statement", "income-statement.pdf"),
            DocumentSeed("donation_receipt", "donation-receipt.pdf"),
        ),
        events=(
            EventSeed("payg_income", "income", 84000.0, "PAYG income"),
            EventSeed(
                "donation",
                "deduction",
                250.0,
                "Donation to Example Charity",
                metadata={
                    "schema_version": "2026.1",
                    "charity_name": "Example Charity",
                    "dgr_confirmed": True,
                    "donation_amount": 250.0,
                    "donation_date": "2025-03-15",
                    "receipt_available": True,
                },
            ),
        ),
        expected_obligation_keys={"donation_receipt"},
        expected_event_categories={"payg_income", "donation"},
        expected_review_categories={"payg_income", "donation"},
        expected_journey_state="ready",
        expected_review_state="ready",
        expected_evidence_state="blocked",
        expected_export_can_export=True,
        expected_evidence_would_block_export=True,
        expected_explanation_categories={"donation"},
    ),
    BetaScenario(
        scenario_id="BETA-005",
        title="PAYG plus work expenses",
        profile={"employment_type": "employee"},
        answers={"employment_type": "employee", "has_work_expenses": "yes"},
        documents=(
            DocumentSeed("income_statement", "income-statement.pdf"),
            DocumentSeed("work_expense_receipt", "laptop-receipt.pdf"),
            DocumentSeed("invoice", "subscription-invoice.pdf"),
        ),
        events=(
            EventSeed("payg_income", "income", 84000.0, "PAYG income"),
            EventSeed(
                "work_expense",
                "deduction",
                1200.0,
                "Laptop work expense",
                metadata={
                    "schema_version": "2026.1",
                    "expense_type": "equipment",
                    "vendor": "Example Store",
                    "work_related_percentage": 80,
                    "receipt_available": True,
                },
            ),
            EventSeed(
                "work_expense",
                "deduction",
                180.0,
                "Professional subscription",
                metadata={
                    "schema_version": "2026.1",
                    "expense_type": "subscription",
                    "work_related_percentage": 100,
                    "receipt_available": True,
                },
            ),
        ),
        expected_obligation_keys={"work_expense_receipt"},
        expected_event_categories={"payg_income", "work_expense"},
        expected_review_categories={"payg_income", "work_expense"},
        expected_journey_state="ready",
        expected_review_state="ready",
        expected_evidence_state="blocked",
        expected_export_can_export=True,
        expected_evidence_would_block_export=True,
        expected_explanation_categories={"work_expense"},
    ),
    BetaScenario(
        scenario_id="BETA-006",
        title="PAYG plus managed fund",
        profile={"employment_type": "employee", "has_investments": True},
        answers={"employment_type": "employee", "has_investments": "yes", "investment_type": "managed_fund"},
        documents=(
            DocumentSeed("income_statement", "income-statement.pdf"),
            DocumentSeed("managed_fund_statement", "managed-fund-tax-statement.pdf"),
        ),
        events=(
            EventSeed("payg_income", "income", 84000.0, "PAYG income"),
            EventSeed(
                "managed_fund_distribution",
                "investment_income",
                1600.0,
                "Managed fund distribution",
                metadata={
                    "schema_version": "2026.1",
                    "fund_name": "Example Managed Fund",
                    "distribution_amount": 1600.0,
                    "capital_gains_component": 450.0,
                    "foreign_income_component": 120.0,
                    "distribution_date": "2025-06-20",
                },
            ),
        ),
        expected_obligation_keys=set(),
        expected_event_categories={"payg_income", "managed_fund_distribution"},
        expected_review_categories={"payg_income", "managed_fund_distribution"},
        expected_journey_state="ready",
        expected_review_state="ready",
        expected_evidence_state="ready",
        expected_export_can_export=True,
        expected_evidence_would_block_export=False,
        expected_explanation_categories={"managed_fund_distribution"},
        known_gap_obligation_keys={"managed_fund_statement"},
    ),
    BetaScenario(
        scenario_id="BETA-007",
        title="PAYG plus shares",
        profile={"employment_type": "employee", "has_investments": True},
        answers={"employment_type": "employee", "has_investments": "yes", "investment_type": "shares"},
        documents=(
            DocumentSeed("income_statement", "income-statement.pdf"),
            DocumentSeed("broker_contract_note", "shares-buy-contract.pdf"),
            DocumentSeed("broker_contract_note", "shares-sell-contract.pdf"),
        ),
        events=(
            EventSeed("payg_income", "income", 84000.0, "PAYG income"),
            EventSeed(
                "shares_acquisition",
                "investment_position",
                5000.0,
                "Share acquisition",
                metadata={
                    "schema_version": "2026.1",
                    "stock_code": "ABC",
                    "units": 100,
                    "price_per_unit": 50.0,
                    "brokerage_fee": 20.0,
                    "purchase_date": "2024-09-01",
                },
            ),
            EventSeed(
                "capital_gain",
                "capital",
                700.0,
                "Share disposal gain",
                metadata={
                    "schema_version": "2026.1",
                    "asset_class": "shares",
                    "stock_code": "ABC",
                    "purchase_date": "2024-09-01",
                    "disposal_date": "2025-04-10",
                    "cost_base": 5020.0,
                    "capital_proceeds": 5720.0,
                },
            ),
        ),
        expected_obligation_keys=set(),
        expected_event_categories={"payg_income", "shares_acquisition", "capital_gain"},
        expected_review_categories={"payg_income", "shares_acquisition", "capital_gain"},
        expected_journey_state="ready",
        expected_review_state="ready",
        expected_evidence_state="ready",
        expected_export_can_export=True,
        expected_evidence_would_block_export=False,
        expected_explanation_categories={"shares_acquisition", "capital_gain"},
        known_gap_obligation_keys={"share_contract_note"},
    ),
    BetaScenario(
        scenario_id="BETA-008",
        title="PAYG plus crypto",
        profile={"employment_type": "employee", "has_investments": True, "has_crypto": True},
        answers={"employment_type": "employee", "has_investments": "yes", "investment_type": "crypto"},
        documents=(
            DocumentSeed("income_statement", "income-statement.pdf"),
            DocumentSeed("crypto_exchange_statement", "crypto-transactions.csv"),
        ),
        events=(
            EventSeed("payg_income", "income", 84000.0, "PAYG income"),
            EventSeed(
                "crypto_acquisition",
                "investment_position",
                2000.0,
                "Crypto acquisition",
                metadata={
                    "schema_version": "2026.1",
                    "coin": "BTC",
                    "amount_units": 0.05,
                    "purchase_price": 2000.0,
                    "purchase_date": "2024-08-01",
                },
            ),
            EventSeed(
                "capital_loss",
                "capital",
                300.0,
                "Crypto disposal loss",
                metadata={
                    "schema_version": "2026.1",
                    "asset_class": "crypto",
                    "coin": "BTC",
                    "disposal_date": "2025-02-01",
                    "cost_base": 1200.0,
                    "capital_proceeds": 900.0,
                },
            ),
            EventSeed(
                "crypto_staking_income",
                "investment_income",
                80.0,
                "Crypto staking rewards",
                metadata={
                    "schema_version": "2026.1",
                    "coin": "ETH",
                    "income_amount": 80.0,
                    "income_date": "2025-01-15",
                },
            ),
        ),
        expected_obligation_keys=set(),
        expected_event_categories={"payg_income", "crypto_acquisition", "capital_loss", "crypto_staking_income"},
        expected_review_categories={"payg_income", "crypto_acquisition", "capital_loss", "crypto_staking_income"},
        expected_journey_state="ready",
        expected_review_state="ready",
        expected_evidence_state="ready",
        expected_export_can_export=True,
        expected_evidence_would_block_export=False,
        expected_explanation_categories={"crypto_acquisition", "capital_loss", "crypto_staking_income"},
        known_gap_obligation_keys={"crypto_exchange_statement"},
    ),
]


@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


async def _seed_workspace(db: AsyncSession, scenario: BetaScenario) -> Workspace:
    workspace = Workspace(
        name=f"{scenario.scenario_id} {scenario.title}",
        financial_year=FY,
        status="active",
    )
    db.add(workspace)
    await db.flush()

    profile = TaxProfile(
        workspace_id=workspace.id,
        financial_year=FY,
        **scenario.profile,
    )
    db.add(profile)
    db.add(
        InterviewSession(
            workspace_id=workspace.id,
            financial_year=FY,
            state="awaiting_evidence",
            answers=scenario.answers,
            completed_steps=list(scenario.answers),
            skipped_steps=[],
            branch_path=[],
            pending_queue=[],
            activated_skills=[],
        )
    )
    await db.commit()
    await db.refresh(workspace)
    return workspace


async def _seed_documents(db: AsyncSession, workspace: Workspace, seeds: tuple[DocumentSeed, ...]) -> dict[str, Document]:
    docs: dict[str, Document] = {}
    for idx, seed in enumerate(seeds):
        doc = Document(
            workspace_id=workspace.id,
            financial_year=workspace.financial_year,
            original_filename=seed.filename,
            storage_key=f"{workspace.id}/{seed.filename}",
            file_type="application/pdf" if not seed.filename.endswith(".csv") else "text/csv",
            file_size_bytes=1024,
            sha256_hash=f"{workspace.id.replace('-', '')}{idx:032d}"[:64].ljust(64, "0"),
            document_type=seed.document_type,
            status="ready",
        )
        db.add(doc)
        docs[seed.filename] = doc
    await db.commit()
    for doc in docs.values():
        await db.refresh(doc)
    return docs


async def _seed_events_and_review_items(
    db: AsyncSession,
    workspace: Workspace,
    seeds: tuple[EventSeed, ...],
) -> list[TaxEvent]:
    review_engine = ReviewEngine()
    events: list[TaxEvent] = []
    for seed in seeds:
        event = TaxEvent(
            workspace_id=workspace.id,
            financial_year=workspace.financial_year,
            event_type=seed.event_type,
            category=seed.category,
            description=seed.description,
            amount=seed.amount,
            date=seed.date,
            source="manual_entry",
            status=seed.status,
            review_status="user_confirmed" if seed.status == "confirmed" else "pending",
            event_metadata=seed.metadata,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        item = await review_engine.create_review_item(event, db)
        item.status = seed.status
        item.user_action = "confirmed" if seed.status == "confirmed" else None
        event.status = seed.status
        event.review_status = "user_confirmed" if seed.status == "confirmed" else "pending"
        await db.commit()
        await db.refresh(event)
        events.append(event)
    return events


async def _scenario_summary(db: AsyncSession, workspace: Workspace, scenario: BetaScenario) -> dict:
    obligations = (
        await db.execute(
            select(EvidenceObligation).where(EvidenceObligation.workspace_id == workspace.id)
        )
    ).scalars().all()
    review_items = (
        await db.execute(select(ReviewItem).where(ReviewItem.workspace_id == workspace.id))
    ).scalars().all()
    readiness_2_0 = await _build_readiness_2_0(workspace.id, db)
    export_result = await ExportEngine().check_eligibility(workspace.id, db)
    preview = await ExportEligibilityService().build_preview(
        workspace_id=workspace.id,
        financial_year=workspace.financial_year,
        db=db,
    )
    return {
        "scenario": scenario.scenario_id,
        "obligations": sorted(o.obligation_key for o in obligations),
        "review_items": sorted(i.category for i in review_items),
        "readiness_state": readiness_2_0["overall"]["state"],
        "journey_state": readiness_2_0["journey"]["state"],
        "review_state": readiness_2_0["review"]["state"],
        "evidence_state": readiness_2_0["evidence"]["state"],
        "export_status": {
            "can_export": export_result.can_export,
            "would_block_export": preview.would_block_export,
        },
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.scenario_id for s in SCENARIOS])
async def test_beta_dry_run_scenario_outputs(db_session: AsyncSession, scenario: BetaScenario):
    workspace = await _seed_workspace(db_session, scenario)
    await _seed_documents(db_session, workspace, scenario.documents)
    events = await _seed_events_and_review_items(db_session, workspace, scenario.events)

    obligations = await reconcile_evidence_obligations(
        workspace.id,
        workspace.financial_year,
        db_session,
    )
    obligation_keys = {o.obligation_key for o in obligations}
    assert scenario.expected_obligation_keys <= obligation_keys
    assert scenario.known_gap_obligation_keys.isdisjoint(obligation_keys)

    event_categories = {event.category for event in events}
    assert scenario.expected_event_categories <= event_categories
    assert "capital_gain" not in event_categories - scenario.expected_event_categories
    assert "capital_loss" not in event_categories - scenario.expected_event_categories

    review_items = (
        await db_session.execute(select(ReviewItem).where(ReviewItem.workspace_id == workspace.id))
    ).scalars().all()
    review_categories = {item.category for item in review_items}
    assert scenario.expected_review_categories <= review_categories

    readiness_2_0 = await _build_readiness_2_0(workspace.id, db_session)
    assert readiness_2_0["journey"]["state"] == scenario.expected_journey_state
    assert readiness_2_0["review"]["state"] == scenario.expected_review_state
    assert readiness_2_0["evidence"]["state"] == scenario.expected_evidence_state

    export_result = await ExportEngine().check_eligibility(workspace.id, db_session)
    preview = await ExportEligibilityService().build_preview(
        workspace_id=workspace.id,
        financial_year=workspace.financial_year,
        db=db_session,
    )
    assert export_result.can_export is scenario.expected_export_can_export
    assert preview.would_block_export is scenario.expected_evidence_would_block_export

    for event in events:
        if event.category in scenario.expected_explanation_categories:
            explanation = build_tax_item_explanation(
                target_type="review_item",
                target_id=event.id,
                category=event.category,
                rule_version=event.event_metadata.get("schema_version") if event.event_metadata else None,
            )
            assert explanation["plain_english_summary"]
            assert explanation["what_user_should_check"]
            assert explanation["evidence_expected"]

    for obligation in obligations:
        explanation = build_evidence_obligation_explanation(
            target_id=obligation.id,
            obligation_key=obligation.obligation_key,
            obligation_category=obligation.category,
            rule_version=obligation.rule_version,
        )
        assert explanation["plain_english_summary"]
        assert explanation["rule_version"] == obligation.rule_version

    summary = await _scenario_summary(db_session, workspace, scenario)
    print(f"BETA_DRY_RUN_SUMMARY {summary}")


@pytest.mark.asyncio
async def test_beta_dry_run_harness_covers_required_scenarios():
    scenario_titles = {scenario.title for scenario in SCENARIOS}
    assert scenario_titles == {
        "PAYG only with bank interest",
        "PAYG plus WFH with evidence supplied",
        "PAYG plus WFH with evidence missing",
        "PAYG plus donations",
        "PAYG plus work expenses",
        "PAYG plus managed fund",
        "PAYG plus shares",
        "PAYG plus crypto",
    }
