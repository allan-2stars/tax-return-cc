"""
Tests for M10 Phase 6 — manual event creation and receipt attachment.
"""
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from unittest.mock import patch

from app.db.models import TaxEvent, ReviewItem as ReviewItemModel, Workspace, TaxProfile, Document


@pytest_asyncio.fixture(autouse=True)
async def patch_async_session_local(test_engine, monkeypatch):
    import app.db.base as db_base
    test_maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(db_base, "AsyncSessionLocal", test_maker)


@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def workspace(db_session):
    ws = Workspace(name="Events Test WS", financial_year="2024-25", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest_asyncio.fixture
async def existing_event(db_session, workspace):
    evt = TaxEvent(
        workspace_id=workspace.id,
        financial_year="2024-25",
        event_type="deduction",
        category="work_expense",
        description="Laptop stand",
        amount=89.00,
        date="2025-08-01",
        source="manual_entry",
        status="needs_user_review",
        risk_level="low",
    )
    db_session.add(evt)
    await db_session.commit()
    await db_session.refresh(evt)
    return evt


@pytest.mark.asyncio
async def test_create_manual_event_one_off_creates_tax_event_and_review_item(
    db_session, workspace
):
    """POST /events/manual (one-off) creates 1 TaxEvent + 1 ReviewItem."""
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()

    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None

        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="deduction",
            category="work_subscription",
            description="Spotify",
            amount=119.88,
            date="2025-09-01",
            frequency="one_off",
            note=None,
            periods=None,
            db=db_session,
        )

    assert len(events) == 1
    assert events[0].source == "manual_entry"
    assert events[0].description == "Spotify"
    assert events[0].amount == 119.88

    result = await db_session.execute(
        select(ReviewItemModel).where(ReviewItemModel.workspace_id == workspace.id)
    )
    items = result.scalars().all()
    assert len(items) == 1
    assert items[0].tax_event_id == events[0].id


@pytest.mark.asyncio
async def test_create_manual_event_monthly_creates_grouped_events(
    db_session, workspace
):
    """Monthly recurring with 2 periods creates 2 TaxEvents with same group_id."""
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()

    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None

        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="deduction",
            category="work_subscription",
            description="Surfshark VPN",
            amount=0,
            date="2025-07-01",
            frequency="monthly",
            note=None,
            periods=[
                {"months": 3, "amount_per_month": 17.0},
                {"months": 8, "amount_per_month": 20.0},
            ],
            db=db_session,
        )

    assert len(events) == 2
    assert events[0].group_id == events[1].group_id
    assert events[0].group_id is not None
    assert events[0].amount == 51.0   # 3 × 17.0
    assert events[1].amount == 160.0  # 8 × 20.0
    assert all(e.is_recurring for e in events)
    assert "2 periods" in events[0].group_display
    assert "$211.00 total" in events[0].group_display


@pytest.mark.asyncio
async def test_attach_receipt_links_document_no_new_event(
    db_session, workspace, existing_event
):
    """attach_receipt links a Document to an existing TaxEvent, no new event created."""
    import tempfile
    from app.engines.evidence import EvidenceEngine
    from app.storage.local import LocalStorageBackend

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorageBackend(base_path=tmpdir)
        engine = EvidenceEngine(db=db_session, storage=storage)

        fake_pdf = b"%PDF-1.4 1 0 obj<</Type /Catalog>> endobj"

        doc = await engine.attach_receipt(
            event_id=existing_event.id,
            workspace_id=workspace.id,
            file_data=fake_pdf,
            filename="receipt.pdf",
        )

    assert doc.id is not None
    assert doc.workspace_id == workspace.id

    await db_session.refresh(existing_event)
    assert existing_event.document_id == doc.id

    result = await db_session.execute(
        select(TaxEvent).where(TaxEvent.workspace_id == workspace.id)
    )
    all_events = result.scalars().all()
    assert len(all_events) == 1


@pytest.mark.asyncio
async def test_create_manual_event_stores_metadata(db_session, workspace):
    """metadata dict is persisted on the TaxEvent."""
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    meta = {
        "investment_sub_type": "shares",
        "transaction_type": "buy",
        "platform": "CommSec",
        "stock_code": "CBA",
        "exchange": "ASX",
        "units": 100,
        "price_per_unit": 82.50,
        "brokerage_fee": 9.95,
        "purchase_date": "2025-08-15",
    }

    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="investment",
            category="capital_gain",
            description="Shares Buy: 100 × CBA @ $82.50",
            amount=8259.95,
            date="2025-08-15",
            frequency="one_off",
            note=None,
            periods=None,
            metadata=meta,
            db=db_session,
        )

    assert events[0].event_metadata == meta


@pytest.mark.asyncio
async def test_create_manual_event_accepts_shares_acquisition_category(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    meta = {
        "investment_sub_type": "shares",
        "transaction_type": "buy",
        "platform": "CommSec",
        "stock_code": "CBA",
        "exchange": "ASX",
        "units": 100,
        "price_per_unit": 82.50,
        "brokerage_fee": 9.95,
        "purchase_date": "2025-08-15",
    }

    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="investment",
            category="shares_acquisition",
            description="Shares Buy: 100 × CBA @ $82.50",
            amount=8259.95,
            date="2025-08-15",
            frequency="one_off",
            note=None,
            periods=None,
            metadata=meta,
            db=db_session,
        )

    assert events[0].category == "shares_acquisition"


@pytest.mark.asyncio
async def test_create_manual_event_accepts_crypto_acquisition_category(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    meta = {
        "investment_sub_type": "crypto",
        "transaction_type": "buy",
        "exchange": "CoinSpot",
        "coin": "BTC",
        "amount_units": 1.0,
        "purchase_price": 100000.0,
        "transaction_fee": 100.0,
        "purchase_date": "2025-08-15",
    }

    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="investment",
            category="crypto_acquisition",
            description="Crypto Buy: 1 BTC",
            amount=100100.0,
            date="2025-08-15",
            frequency="one_off",
            note=None,
            periods=None,
            metadata=meta,
            db=db_session,
        )

    assert events[0].category == "crypto_acquisition"


@pytest.mark.asyncio
async def test_create_manual_event_accepts_bank_interest_with_statement_period(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="investment",
            category="bank_interest",
            description="Bank Interest",
            amount=120.0,
            date="2025-06-30",
            frequency="annual",
            note=None,
            periods=None,
            metadata={
                "investment_sub_type": "bank_interest",
                "bank_name": "CBA",
                "account_type": "Savings",
                "interest_amount": 120.0,
                "statement_period_start": "2024-07-01",
                "statement_period_end": "2025-06-30",
                "financial_year": "2024-25",
            },
            db=db_session,
        )
    assert len(events) == 1


@pytest.mark.asyncio
async def test_create_manual_event_accepts_legacy_bank_interest_without_period(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="investment",
            category="bank_interest",
            description="Bank Interest legacy",
            amount=80.0,
            date="2025-06-30",
            frequency="annual",
            note=None,
            periods=None,
            metadata={
                "investment_sub_type": "bank_interest",
                "bank_name": "NAB",
                "account_type": "Savings",
                "interest_amount": 80.0,
            },
            db=db_session,
        )
    assert len(events) == 1


@pytest.mark.asyncio
async def test_create_manual_event_rejects_invalid_bank_interest_period(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        with pytest.raises(ValueError, match="statement_period_start"):
            await engine.create_manual_event(
                workspace_id=workspace.id,
                financial_year="2024-25",
                event_type="investment",
                category="bank_interest",
                description="Bank Interest invalid period",
                amount=100.0,
                date="2025-06-30",
                frequency="annual",
                note=None,
                periods=None,
                metadata={
                    "investment_sub_type": "bank_interest",
                    "bank_name": "ANZ",
                    "account_type": "Savings",
                    "interest_amount": 100.0,
                    "statement_period_start": "2025-06-30",
                    "statement_period_end": "2024-07-01",
                },
                db=db_session,
            )


@pytest.mark.asyncio
async def test_create_manual_event_accepts_valid_managed_fund_metadata(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="investment",
            category="managed_fund_distribution",
            description="Managed Fund Distribution",
            amount=500.0,
            date="2025-06-30",
            frequency="one_off",
            note=None,
            periods=None,
            metadata={
                "investment_sub_type": "managed_fund",
                "fund_name": "Vanguard High Growth",
                "fund_manager": "Vanguard",
                "distribution_amount": 500.0,
                "capital_gains_component": 100.0,
                "foreign_income_component": 50.0,
                "tfn_withholding": 0.0,
                "distribution_date": "2025-06-30",
            },
            db=db_session,
        )
    assert len(events) == 1


@pytest.mark.asyncio
async def test_create_manual_event_rejects_managed_fund_missing_fund_name(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        with pytest.raises(ValueError, match="fund_name"):
            await engine.create_manual_event(
                workspace_id=workspace.id,
                financial_year="2024-25",
                event_type="investment",
                category="managed_fund_distribution",
                description="Managed Fund Distribution",
                amount=500.0,
                date="2025-06-30",
                frequency="one_off",
                note=None,
                periods=None,
                metadata={
                    "investment_sub_type": "managed_fund",
                    "distribution_amount": 500.0,
                    "capital_gains_component": 100.0,
                    "foreign_income_component": 50.0,
                    "tfn_withholding": 0.0,
                    "distribution_date": "2025-06-30",
                },
                db=db_session,
            )


@pytest.mark.asyncio
async def test_create_manual_event_rejects_managed_fund_negative_component(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        with pytest.raises(ValueError, match="capital_gains_component"):
            await engine.create_manual_event(
                workspace_id=workspace.id,
                financial_year="2024-25",
                event_type="investment",
                category="managed_fund_distribution",
                description="Managed Fund Distribution",
                amount=500.0,
                date="2025-06-30",
                frequency="one_off",
                note=None,
                periods=None,
                metadata={
                    "investment_sub_type": "managed_fund",
                    "fund_name": "Fund X",
                    "distribution_amount": 500.0,
                    "capital_gains_component": -1.0,
                    "foreign_income_component": 50.0,
                    "tfn_withholding": 0.0,
                    "distribution_date": "2025-06-30",
                },
                db=db_session,
            )


@pytest.mark.asyncio
async def test_create_manual_event_needs_agent_review_sets_status_on_event_and_review_item(
    db_session, workspace
):
    """review_status='needs_agent_review' propagates to TaxEvent and ReviewItem."""
    from app.engines.review import ReviewEngine
    from sqlalchemy import select
    from app.db.models import ReviewItem as ReviewItemModel

    engine = ReviewEngine()

    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="investment",
            category="foreign_income",
            description="US Dividends",
            amount=500.0,
            date="2025-03-01",
            frequency="one_off",
            note=None,
            periods=None,
            metadata={
                "investment_sub_type": "foreign_income",
                "country": "United States",
                "income_type": "Dividends",
                "foreign_amount": 300.0,
                "currency": "USD",
                "exchange_rate": 1.5,
                "income_date": "2025-03-01",
                "foreign_tax_paid": 0.0,
            },
            review_status="needs_agent_review",
            db=db_session,
        )

    assert events[0].status == "needs_agent_review"
    assert events[0].risk_level == "high"
    assert events[0].possible_duplicate is False

    result = await db_session.execute(
        select(ReviewItemModel).where(ReviewItemModel.tax_event_id == events[0].id)
    )
    item = result.scalar_one()
    assert item.status == "needs_agent_review"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("description", "amount", "date", "metadata", "match_message"),
    [
        (
            "Crypto Buy invalid coin",
            100.0,
            "2025-01-01",
            {
                "investment_sub_type": "crypto",
                "transaction_type": "buy",
                "exchange": "CoinSpot",
                "coin": "btc!",
                "amount_units": 1.0,
                "purchase_price": 100.0,
                "transaction_fee": 0.0,
                "purchase_date": "2025-01-01",
            },
            "Coin/token",
        ),
        (
            "Crypto Buy zero units",
            100.0,
            "2025-01-01",
            {
                "investment_sub_type": "crypto",
                "transaction_type": "buy",
                "exchange": "CoinSpot",
                "coin": "BTC",
                "amount_units": 0.0,
                "purchase_price": 100.0,
                "transaction_fee": 0.0,
                "purchase_date": "2025-01-01",
            },
            "amount_units",
        ),
        (
            "Shares Sell invalid stock code",
            100.0,
            "2025-02-01",
            {
                "investment_sub_type": "shares",
                "transaction_type": "sell",
                "platform": "CommSec",
                "stock_code": "CBA-",
                "exchange": "ASX",
                "units": 10,
                "sale_price_per_unit": 10,
                "purchase_price_per_unit": 8,
                "brokerage_fee": 1,
                "sale_date": "2025-02-01",
                "purchase_date": "2025-01-01",
            },
            "Stock code",
        ),
        (
            "Shares Sell purchase after sale",
            100.0,
            "2025-02-01",
            {
                "investment_sub_type": "shares",
                "transaction_type": "sell",
                "platform": "CommSec",
                "stock_code": "CBA",
                "exchange": "ASX",
                "units": 10,
                "sale_price_per_unit": 10,
                "purchase_price_per_unit": 8,
                "brokerage_fee": 1,
                "sale_date": "2025-01-01",
                "purchase_date": "2025-02-01",
            },
            "purchase_date",
        ),
        (
            "Foreign Income invalid currency",
            100.0,
            "2025-01-01",
            {
                "investment_sub_type": "foreign_income",
                "country": "United States",
                "income_type": "Dividends",
                "foreign_amount": 100,
                "currency": "US1D",
                "exchange_rate": 1.5,
                "income_date": "2025-01-01",
            },
            "Currency code",
        ),
        (
            "Foreign Income non-positive amount",
            100.0,
            "2025-01-01",
            {
                "investment_sub_type": "foreign_income",
                "country": "United States",
                "income_type": "Dividends",
                "foreign_amount": 0,
                "currency": "USD",
                "exchange_rate": 1.5,
                "income_date": "2025-01-01",
            },
            "foreign_amount",
        ),
    ],
)
async def test_create_manual_event_rejects_invalid_investment_metadata_and_does_not_persist(
    db_session, workspace, description, amount, date, metadata, match_message
):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    before_events = (await db_session.execute(select(TaxEvent))).scalars().all()
    before_items = (await db_session.execute(select(ReviewItemModel))).scalars().all()

    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        with pytest.raises(ValueError, match=match_message):
            await engine.create_manual_event(
                workspace_id=workspace.id,
                financial_year="2024-25",
                event_type="investment",
                category="crypto",
                description=description,
                amount=amount,
                date=date,
                frequency="one_off",
                note=None,
                periods=None,
                metadata=metadata,
                db=db_session,
            )

    after_events = (await db_session.execute(select(TaxEvent))).scalars().all()
    after_items = (await db_session.execute(select(ReviewItemModel))).scalars().all()
    assert len(after_events) == len(before_events)
    assert len(after_items) == len(before_items)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("description", "note", "match_message"),
    [
        ("x" * 501, None, "Description"),
        ("Valid description", "x" * 5001, "Note"),
    ],
)
async def test_create_manual_event_rejects_overlong_description_or_note_and_does_not_persist(
    db_session, workspace, description, note, match_message
):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    before_events = (await db_session.execute(select(TaxEvent))).scalars().all()
    before_items = (await db_session.execute(select(ReviewItemModel))).scalars().all()

    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        with pytest.raises(ValueError, match=match_message):
            await engine.create_manual_event(
                workspace_id=workspace.id,
                financial_year="2024-25",
                event_type="deduction",
                category="work_expense",
                description=description,
                amount=10.0,
                date="2025-01-01",
                frequency="one_off",
                note=note,
                periods=None,
                db=db_session,
            )

    after_events = (await db_session.execute(select(TaxEvent))).scalars().all()
    after_items = (await db_session.execute(select(ReviewItemModel))).scalars().all()
    assert len(after_events) == len(before_events)
    assert len(after_items) == len(before_items)


@pytest.mark.asyncio
async def test_create_manual_event_accepts_valid_donation_metadata(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="deduction",
            category="donation",
            description="Donation to Red Cross",
            amount=150.0,
            date="2025-01-10",
            frequency="one_off",
            note=None,
            periods=None,
            metadata={
                "schema_version": "2026.1",
                "charity_name": "Red Cross",
                "abn": "12 345 678 901",
                "dgr_confirmed": True,
                "donation_amount": 150.0,
                "donation_date": "2025-01-10",
                "receipt_available": True,
            },
            db=db_session,
        )
    assert len(events) == 1


@pytest.mark.asyncio
async def test_create_manual_event_rejects_invalid_donation_metadata(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        with pytest.raises(ValueError, match="charity_name"):
            await engine.create_manual_event(
                workspace_id=workspace.id,
                financial_year="2024-25",
                event_type="deduction",
                category="donation",
                description="Donation",
                amount=100.0,
                date="2025-01-10",
                frequency="one_off",
                note=None,
                periods=None,
                metadata={
                    "schema_version": "2026.1",
                    "dgr_confirmed": True,
                    "donation_amount": 100.0,
                    "donation_date": "2025-01-10",
                    "receipt_available": False,
                },
                db=db_session,
            )


@pytest.mark.asyncio
async def test_create_manual_event_accepts_valid_work_expense_metadata(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="deduction",
            category="work_expense",
            description="Laptop stand",
            amount=90.0,
            date="2025-02-02",
            frequency="one_off",
            note=None,
            periods=None,
            metadata={
                "schema_version": "2026.1",
                "expense_type": "office_supplies",
                "vendor": "Officeworks",
                "amount": 90.0,
                "purchase_date": "2025-02-02",
                "work_related_percentage": 100,
                "receipt_available": True,
            },
            db=db_session,
        )
    assert len(events) == 1


@pytest.mark.asyncio
async def test_create_manual_event_rejects_invalid_work_related_percentage(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        with pytest.raises(ValueError, match="work_related_percentage"):
            await engine.create_manual_event(
                workspace_id=workspace.id,
                financial_year="2024-25",
                event_type="deduction",
                category="work_expense",
                description="Laptop stand",
                amount=90.0,
                date="2025-02-02",
                frequency="one_off",
                note=None,
                periods=None,
                metadata={
                    "schema_version": "2026.1",
                    "expense_type": "office_supplies",
                    "amount": 90.0,
                    "purchase_date": "2025-02-02",
                    "work_related_percentage": 120,
                    "receipt_available": True,
                },
                db=db_session,
            )


@pytest.mark.asyncio
async def test_create_manual_event_accepts_valid_wfh_fixed_rate_metadata(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="deduction",
            category="wfh_deduction",
            description="WFH fixed rate claim",
            amount=0.0,
            date="2025-03-01",
            frequency="one_off",
            note=None,
            periods=None,
            metadata={
                "schema_version": "2026.1",
                "method": "fixed_rate",
                "financial_year": "2024-25",
                "hours": 200,
                "evidence_available": True,
            },
            db=db_session,
        )
    assert len(events) == 1


@pytest.mark.asyncio
async def test_create_manual_event_accepts_valid_wfh_actual_cost_metadata(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="deduction",
            category="wfh_deduction",
            description="WFH actual cost claim",
            amount=350.0,
            date="2025-03-01",
            frequency="one_off",
            note=None,
            periods=None,
            metadata={
                "schema_version": "2026.1",
                "method": "actual_cost",
                "financial_year": "2024-25",
                "amount": 350.0,
                "evidence_available": False,
            },
            db=db_session,
        )
    assert len(events) == 1


@pytest.mark.asyncio
async def test_create_manual_event_rejects_invalid_wfh_method(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        with pytest.raises(ValueError, match="method must be one of"):
            await engine.create_manual_event(
                workspace_id=workspace.id,
                financial_year="2024-25",
                event_type="deduction",
                category="wfh_deduction",
                description="WFH",
                amount=10.0,
                date="2025-03-01",
                frequency="one_off",
                note=None,
                periods=None,
                metadata={
                    "schema_version": "2026.1",
                    "method": "invalid",
                    "financial_year": "2024-25",
                    "evidence_available": True,
                },
                db=db_session,
            )


@pytest.mark.asyncio
async def test_create_manual_event_legacy_generic_payload_still_accepted_for_donation(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="deduction",
            category="donation",
            description="Legacy generic donation",
            amount=80.0,
            date="2025-02-01",
            frequency="one_off",
            note=None,
            periods=None,
            metadata=None,
            db=db_session,
        )
    assert len(events) == 1


@pytest.mark.asyncio
async def test_create_manual_event_accepts_foreign_income_with_optional_audit_fields(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="investment",
            category="foreign_income",
            description="Foreign Income with audit",
            amount=650.0,
            date="2025-03-01",
            frequency="one_off",
            note=None,
            periods=None,
            metadata={
                "investment_sub_type": "foreign_income",
                "country": "United States",
                "income_type": "Dividends",
                "foreign_amount": 1000.0,
                "currency": "USD",
                "exchange_rate": 0.65,
                "aud_amount": 650.0,
                "income_date": "2025-03-01",
                "foreign_tax_paid": 0.0,
                "fx_source": "ATO annual average",
                "source_document_reference": "Broker-Statement-2025-03",
            },
            review_status="needs_agent_review",
            db=db_session,
        )
    assert len(events) == 1


@pytest.mark.asyncio
async def test_create_manual_event_rejects_foreign_income_invalid_exchange_rate(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        with pytest.raises(ValueError, match="exchange_rate"):
            await engine.create_manual_event(
                workspace_id=workspace.id,
                financial_year="2024-25",
                event_type="investment",
                category="foreign_income",
                description="Foreign Income invalid rate",
                amount=100.0,
                date="2025-03-01",
                frequency="one_off",
                note=None,
                periods=None,
                metadata={
                    "investment_sub_type": "foreign_income",
                    "country": "United States",
                    "income_type": "Dividends",
                    "foreign_amount": 1000.0,
                    "currency": "USD",
                    "exchange_rate": 0.0,
                    "income_date": "2025-03-01",
                },
                db=db_session,
            )


@pytest.mark.asyncio
async def test_create_manual_event_rejects_foreign_income_negative_foreign_tax_paid(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        with pytest.raises(ValueError, match="foreign_tax_paid"):
            await engine.create_manual_event(
                workspace_id=workspace.id,
                financial_year="2024-25",
                event_type="investment",
                category="foreign_income",
                description="Foreign Income invalid foreign tax",
                amount=100.0,
                date="2025-03-01",
                frequency="one_off",
                note=None,
                periods=None,
                metadata={
                    "investment_sub_type": "foreign_income",
                    "country": "United States",
                    "income_type": "Dividends",
                    "foreign_amount": 1000.0,
                    "currency": "USD",
                    "exchange_rate": 0.65,
                    "income_date": "2025-03-01",
                    "foreign_tax_paid": -1.0,
                },
                db=db_session,
            )


@pytest.mark.asyncio
async def test_create_manual_event_accepts_legacy_foreign_income_without_aud_amount(db_session, workspace):
    from app.engines.review import ReviewEngine

    engine = ReviewEngine()
    with patch.object(engine._readiness_engine, "recalculate") as mock_recalc:
        mock_recalc.return_value = None
        events = await engine.create_manual_event(
            workspace_id=workspace.id,
            financial_year="2024-25",
            event_type="investment",
            category="foreign_income",
            description="Foreign Income legacy",
            amount=650.0,
            date="2025-03-01",
            frequency="one_off",
            note=None,
            periods=None,
            metadata={
                "investment_sub_type": "foreign_income",
                "country": "United States",
                "income_type": "Dividends",
                "foreign_amount": 1000.0,
                "currency": "USD",
                "exchange_rate": 0.65,
                "income_date": "2025-03-01",
            },
            db=db_session,
        )
    assert len(events) == 1
