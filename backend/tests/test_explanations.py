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
