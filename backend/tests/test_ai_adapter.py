"""
Tests for AIAdapter and ClaudeProvider.

All AI provider calls are mocked — the real Anthropic API is never called.
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.base import (
    AIAdapter,
    AIProvider,
    AIResponse,
    ClassificationResult,
    RiskAssessment,
)
from app.ai.prompts import CLASSIFY_SYSTEM


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_response(content: str, provider: str = "claude", model: str = "claude-sonnet-4-6") -> AIResponse:
    return AIResponse(
        content=content,
        input_tokens=10,
        output_tokens=20,
        provider=provider,
        model=model,
    )


def _classify_json(**kwargs) -> str:
    payload = {
        "document_type": "receipt",
        "confidence": 0.9,
        "skill_id": "employee_tax_au",
        "suggested_category": "work_expense",
        "extracted_amounts": [],
        "notes": "looks like a work receipt",
    }
    payload.update(kwargs)
    return json.dumps(payload)


def _mock_provider(return_value: AIResponse) -> AIProvider:
    provider = MagicMock(spec=AIProvider)
    provider.complete = AsyncMock(return_value=return_value)
    provider.complete_with_search = AsyncMock(return_value=return_value)
    return provider


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session(test_engine):
    maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def patch_async_session_local(test_engine, monkeypatch):
    """Route _fire_audit's AsyncSessionLocal to the test engine."""
    import app.db.base as db_base
    test_maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(db_base, "AsyncSessionLocal", test_maker)


@pytest_asyncio.fixture
async def workspace(db_session):
    from app.db.models import Workspace
    ws = Workspace(name="AI Test WS", financial_year="2024-25", status="active")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


# ── 1. classify returns correct ClassificationResult shape ────────────────────

@pytest.mark.asyncio
async def test_classify_returns_classification_result(workspace):
    provider = _mock_provider(_make_response(_classify_json()))
    adapter = AIAdapter(provider=provider, workspace_id=workspace.id)

    result = await adapter.classify(
        text="Coffee 5.50 at local café",
        fields={"amount": "5.50"},
        profile={"employment_type": "employee"},
    )

    assert isinstance(result, ClassificationResult)
    assert result.document_type == "receipt"
    assert result.confidence == 0.9
    assert result.skill_id == "employee_tax_au"


# ── 2. classify retries on JSON parse failure ─────────────────────────────────

@pytest.mark.asyncio
async def test_classify_retries_on_json_parse_failure(workspace):
    bad = _make_response("not valid json at all")
    good = _make_response(_classify_json())
    provider = MagicMock(spec=AIProvider)
    provider.complete = AsyncMock(side_effect=[bad, bad, good])

    adapter = AIAdapter(provider=provider, workspace_id=workspace.id)
    result = await adapter.classify(text="text", fields=None, profile=None)

    assert provider.complete.call_count == 3
    assert isinstance(result, ClassificationResult)
    assert result.confidence == 0.9


# ── 3. classify returns fallback after 3 failures — never raises ──────────────

@pytest.mark.asyncio
async def test_classify_returns_fallback_after_three_json_failures(workspace):
    provider = MagicMock(spec=AIProvider)
    provider.complete = AsyncMock(return_value=_make_response("not json"))

    adapter = AIAdapter(provider=provider, workspace_id=workspace.id)
    result = await adapter.classify(text="text", fields=None, profile=None)

    assert provider.complete.call_count == 3
    assert isinstance(result, ClassificationResult)
    assert result.confidence == 0.0
    assert result.document_type == "unknown"


# ── 4. classify timeout returns fallback — never raises ──────────────────────

@pytest.mark.asyncio
async def test_classify_timeout_returns_fallback(workspace):
    provider = MagicMock(spec=AIProvider)
    provider.complete = AsyncMock(side_effect=asyncio.TimeoutError())

    adapter = AIAdapter(provider=provider, workspace_id=workspace.id)
    result = await adapter.classify(text="text", fields=None, profile=None)

    assert isinstance(result, ClassificationResult)
    assert result.confidence == 0.0
    assert result.document_type == "unknown"


# ── 5. explain always contains disclaimer ────────────────────────────────────

@pytest.mark.asyncio
async def test_explain_response_contains_disclaimer(workspace):
    disclaimer = "does not constitute tax advice"
    explanation = f"This item appears to be a work expense. {disclaimer} Please discuss with your registered tax agent."
    provider = _mock_provider(_make_response(json.dumps({"explanation": explanation})))
    adapter = AIAdapter(provider=provider, workspace_id=workspace.id)

    result = await adapter.explain(
        event={"description": "Coffee", "amount": 5.50, "date": "2024-07-01", "category": "work_expense", "ai_reasoning": ""},
        profile={"employment_type": "employee", "financial_year": "2024-25"},
    )

    assert "does not constitute tax advice" in result
    assert "registered tax agent" in result


# ── 6. ask always contains disclaimer ────────────────────────────────────────

@pytest.mark.asyncio
async def test_ask_response_contains_disclaimer(workspace):
    disclaimer = "does not constitute tax advice"
    answer = f"You may be able to claim this. {disclaimer} Please discuss with your registered tax agent."
    provider = _mock_provider(_make_response(json.dumps({"answer": answer})))
    adapter = AIAdapter(provider=provider, workspace_id=workspace.id)

    result = await adapter.ask(
        question="Can I claim this coffee?",
        event={"description": "Coffee", "amount": 5.50, "date": "2024-07-01", "category": "work_expense", "ai_reasoning": ""},
        session=None,
    )

    assert "does not constitute tax advice" in result
    assert "registered tax agent" in result


# ── 7. sanitize_for_ai called before every classify ───────────────────────────

@pytest.mark.asyncio
async def test_sanitize_called_before_classify(workspace):
    provider = _mock_provider(_make_response(_classify_json()))
    adapter = AIAdapter(provider=provider, workspace_id=workspace.id)

    with patch("app.ai.base.sanitize_for_ai", wraps=lambda t, f: (t, f)) as mock_san:
        await adapter.classify(
            text="TFN 123-456-789 receipt",
            fields={"merchant": "Café"},
            profile=None,
        )
    mock_san.assert_called_once()


# ── 8. AuditLog written after every classify ──────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log_written_after_classify(db_session, workspace):
    provider = _mock_provider(_make_response(_classify_json()))
    adapter = AIAdapter(provider=provider, workspace_id=workspace.id)

    await adapter.classify(text="text", fields=None, profile=None)

    # Give the fire-and-forget task time to complete (uses its own session via AsyncSessionLocal)
    await asyncio.sleep(0.1)

    from sqlalchemy import select
    from app.db.models import AuditLog
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.workspace_id == workspace.id)
    )
    log = result.scalar_one()
    assert log.ai_operation == "classify"
    assert log.ai_success is True


# ── 9. provider swap yields same output schema ────────────────────────────────

@pytest.mark.asyncio
async def test_provider_swap_same_output_schema(workspace):
    """Replacing ClaudeProvider with a mock yields identical ClassificationResult shape."""
    mock_response = _make_response(_classify_json(), provider="mock", model="mock-v1")
    mock_provider = _mock_provider(mock_response)
    adapter = AIAdapter(provider=mock_provider, workspace_id=workspace.id)

    result = await adapter.classify(text="any text", fields=None, profile=None)

    assert isinstance(result, ClassificationResult)
    assert hasattr(result, "document_type")
    assert hasattr(result, "confidence")
    assert hasattr(result, "skill_id")
    assert hasattr(result, "notes")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("raw_type", "expected"),
    [
        ("annual tax statement", "managed_fund_annual_tax_statement"),
        ("managed fund tax summary", "managed_fund_annual_tax_statement"),
        ("distribution statement", "managed_fund_distribution_statement"),
        ("contract note", "share_buy_contract_note"),
        ("trade confirmation", "share_buy_contract_note"),
        ("sale contract note", "share_sell_contract_note"),
        ("dividend advice", "share_dividend_statement"),
        ("annual trading summary", "share_annual_broker_summary"),
        ("CoinSpot CSV", "crypto_exchange_transaction_export"),
        ("Binance export", "crypto_exchange_transaction_export"),
        ("wallet activity report", "crypto_wallet_activity_export"),
        ("staking report", "crypto_staking_income_statement"),
    ],
)
async def test_classify_normalizes_investment_document_type_aliases(workspace, raw_type, expected):
    provider = _mock_provider(_make_response(_classify_json(document_type=raw_type)))
    adapter = AIAdapter(provider=provider, workspace_id=workspace.id)

    result = await adapter.classify(text="investment document", fields=None, profile=None)

    assert result.document_type == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw_type",
    [
        "receipt",
        "invoice",
        "payg_summary",
        "bank_statement",
        "csv",
        "other",
        "unknown",
    ],
)
async def test_classify_preserves_existing_document_types(workspace, raw_type):
    provider = _mock_provider(_make_response(_classify_json(document_type=raw_type)))
    adapter = AIAdapter(provider=provider, workspace_id=workspace.id)

    result = await adapter.classify(text="legacy document", fields=None, profile=None)

    assert result.document_type == raw_type


def test_classify_prompt_lists_investment_document_categories():
    for expected in [
        "managed_fund_annual_tax_statement",
        "managed_fund_distribution_statement",
        "share_buy_contract_note",
        "share_sell_contract_note",
        "share_dividend_statement",
        "share_annual_broker_summary",
        "crypto_exchange_transaction_export",
        "crypto_wallet_activity_export",
        "crypto_staking_income_statement",
    ]:
        assert expected in CLASSIFY_SYSTEM
