import pytest

from app.services.explanations import (
    build_evidence_obligation_explanation,
    build_tax_item_explanation,
)
from app.services.evidence_rules import CURRENT_EVIDENCE_RULE_VERSION


def test_tax_item_explanations_supported_categories_are_deterministic():
    categories = [
        "bank_interest",
        "donation",
        "work_expense",
        "wfh_deduction",
        "foreign_income",
        "managed_fund_distribution",
        "shares_acquisition",
        "crypto_acquisition",
        "capital_gain",
        "capital_loss",
    ]
    for category in categories:
        payload = build_tax_item_explanation(
            target_type="review_item",
            target_id="ri-1",
            category=category,
            source="review",
        )
        assert payload["target_type"] == "review_item"
        assert payload["target_id"] == "ri-1"
        assert payload["source"] == "review"
        assert payload["plain_english_summary"]
        assert payload["why_it_matters"]
        assert payload["what_user_should_check"]
        assert isinstance(payload["evidence_expected"], list)
        assert payload["confidence_level"] in {"low", "medium", "high"}


def test_tax_item_unknown_category_uses_safe_generic_explanation():
    payload = build_tax_item_explanation(
        target_type="review_item",
        target_id="ri-unknown",
        category="unknown_thing",
        source="review",
    )
    assert payload["category"] == "unknown_thing"
    assert payload["confidence_level"] == "low"
    assert payload["source"] == "review"
    assert "captured for review" in payload["plain_english_summary"].lower()


def test_evidence_obligation_explanation_includes_rule_version():
    payload = build_evidence_obligation_explanation(
        target_id="obl-1",
        obligation_key="donation_receipt",
        obligation_category="deduction",
        rule_version=CURRENT_EVIDENCE_RULE_VERSION,
        source="rule",
    )
    assert payload["target_type"] == "evidence_obligation"
    assert payload["rule_version"] == CURRENT_EVIDENCE_RULE_VERSION
    assert payload["source"] == "rule"
    assert payload["confidence_level"] in {"low", "medium", "high"}


@pytest.mark.parametrize(
    ("obligation_key", "expected_check"),
    [
        ("managed_fund_annual_tax_statement", "annual tax statement or tax summary"),
        ("managed_fund_capital_gains_schedule", "capital gains and cgt components"),
        ("managed_fund_foreign_income_support", "foreign income, foreign tax paid, or foreign tax offset"),
        ("share_buy_contract_note", "contract note or transaction confirmation for share purchases"),
        ("share_sell_contract_note", "contract note or transaction confirmation for share sales"),
        ("share_dividend_statement", "dividend statement"),
        ("share_annual_broker_summary", "annual broker report or transaction summary"),
        ("crypto_exchange_transaction_export", "csv export, annual tax report, or transaction history"),
        ("crypto_disposal_supporting_records", "disposals, swaps, sales, fees, and acquisition cost basis"),
        ("crypto_staking_income_statement", "staking rewards or crypto income"),
        ("crypto_wallet_activity_export", "wallet activity exports or transaction history"),
    ],
)
def test_investment_evidence_obligation_explanations_are_specific(obligation_key, expected_check):
    payload = build_evidence_obligation_explanation(
        target_id="obl-investment",
        obligation_key=obligation_key,
        obligation_category="investment",
        rule_version=CURRENT_EVIDENCE_RULE_VERSION,
        source="rule",
    )
    assert payload["plain_english_summary"]
    assert expected_check in payload["what_user_should_check"].lower()
    assert payload["confidence_level"] in {"medium", "high"}
