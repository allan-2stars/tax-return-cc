from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExplanationTemplate:
    category: str
    plain_english_summary: str
    why_it_matters: str
    what_user_should_check: str
    evidence_expected: list[str]
    confidence_level: str


TAX_CATEGORY_TEMPLATES: dict[str, ExplanationTemplate] = {
    "bank_interest": ExplanationTemplate(
        category="income",
        plain_english_summary="Bank interest was identified as taxable income for review.",
        why_it_matters="Interest may affect your assessable income totals.",
        what_user_should_check="Confirm the institution, period, and interest amount are accurate.",
        evidence_expected=["bank interest statement"],
        confidence_level="high",
    ),
    "donation": ExplanationTemplate(
        category="deduction",
        plain_english_summary="A donation item was added and should be checked for eligibility details.",
        why_it_matters="Donation claims usually depend on recipient status and record support.",
        what_user_should_check="Check charity details, date, amount, and receipt availability.",
        evidence_expected=["donation receipt"],
        confidence_level="medium",
    ),
    "work_expense": ExplanationTemplate(
        category="deduction",
        plain_english_summary="A work-related expense item was recorded for review.",
        why_it_matters="Work-related claims should align with work use and records.",
        what_user_should_check="Check expense type, amount, date, and work-related proportion.",
        evidence_expected=["receipt", "invoice"],
        confidence_level="medium",
    ),
    "wfh_deduction": ExplanationTemplate(
        category="deduction",
        plain_english_summary="A work-from-home deduction was recorded and needs method-aligned records.",
        why_it_matters="WFH claims rely on consistent method inputs and evidence.",
        what_user_should_check="Check method, hours or amount, and financial year alignment.",
        evidence_expected=["timesheet", "work diary", "work-from-home log"],
        confidence_level="medium",
    ),
    "foreign_income": ExplanationTemplate(
        category="income",
        plain_english_summary="Foreign income details were captured for review and conversion checks.",
        why_it_matters="FX conversion and related tax fields can affect outcomes.",
        what_user_should_check="Check currency, exchange rate, AUD amount, and foreign tax paid.",
        evidence_expected=["foreign income statement", "exchange rate record"],
        confidence_level="medium",
    ),
    "managed_fund_distribution": ExplanationTemplate(
        category="investment",
        plain_english_summary="Managed fund distribution components were captured for review.",
        why_it_matters="Distribution components may affect downstream tax treatment.",
        what_user_should_check="Check fund name, distribution amount, components, and date.",
        evidence_expected=["managed fund tax statement"],
        confidence_level="medium",
    ),
    "shares_acquisition": ExplanationTemplate(
        category="investment",
        plain_english_summary="A share acquisition was recorded as a non-disposal investment event.",
        why_it_matters="Acquisition records support future disposal and cost-base checks.",
        what_user_should_check="Check stock code, units, purchase amount, and brokerage.",
        evidence_expected=["broker contract note", "trade confirmation"],
        confidence_level="medium",
    ),
    "crypto_acquisition": ExplanationTemplate(
        category="investment",
        plain_english_summary="A crypto acquisition was recorded as a non-disposal investment event.",
        why_it_matters="Acquisition records support later disposal and value tracing.",
        what_user_should_check="Check token code, quantity, value, and transaction date.",
        evidence_expected=["exchange transaction record", "wallet activity export"],
        confidence_level="medium",
    ),
    "capital_gain": ExplanationTemplate(
        category="investment",
        plain_english_summary="A disposal event indicates a potential capital gain for review.",
        why_it_matters="Disposal outcomes may affect taxable totals.",
        what_user_should_check="Check disposal proceeds, dates, and linked acquisition context.",
        evidence_expected=["sell transaction record", "supporting acquisition records"],
        confidence_level="medium",
    ),
    "capital_loss": ExplanationTemplate(
        category="investment",
        plain_english_summary="A disposal event indicates a potential capital loss for review.",
        why_it_matters="Disposal outcomes may affect taxable totals.",
        what_user_should_check="Check disposal proceeds, dates, and linked acquisition context.",
        evidence_expected=["sell transaction record", "supporting acquisition records"],
        confidence_level="medium",
    ),
}


OBLIGATION_TEMPLATE_BY_KEY: dict[str, ExplanationTemplate] = {
    "private_health_annual_statement": ExplanationTemplate(
        category="evidence_requirement",
        plain_english_summary="Private health details indicate an annual statement should be provided.",
        why_it_matters="This helps confirm private health-related tax details during review.",
        what_user_should_check="Check fund name, member period, and statement financial year.",
        evidence_expected=["private health annual statement"],
        confidence_level="high",
    ),
    "wfh_evidence_records": ExplanationTemplate(
        category="evidence_requirement",
        plain_english_summary="Work-from-home inputs indicate supporting records are expected.",
        why_it_matters="WFH claims usually require method-aligned records.",
        what_user_should_check="Check that hours or cost method evidence matches the selected method.",
        evidence_expected=["timesheet", "work diary", "work-from-home log"],
        confidence_level="high",
    ),
    "donation_receipt": ExplanationTemplate(
        category="evidence_requirement",
        plain_english_summary="A donation entry indicates a receipt should be available.",
        why_it_matters="Donation entries generally rely on documentary support.",
        what_user_should_check="Check charity details, donation date, and amount on the receipt.",
        evidence_expected=["donation receipt"],
        confidence_level="high",
    ),
    "work_expense_receipt": ExplanationTemplate(
        category="evidence_requirement",
        plain_english_summary="A work expense entry indicates a receipt or invoice should be available.",
        why_it_matters="Work-related deductions generally require purchase records.",
        what_user_should_check="Check vendor, date, and amount consistency with the entry.",
        evidence_expected=["receipt", "invoice"],
        confidence_level="high",
    ),
    "bank_interest_statement": ExplanationTemplate(
        category="evidence_requirement",
        plain_english_summary="A bank interest entry suggests a statement should be reviewed.",
        why_it_matters="Statements help verify interest amounts and periods.",
        what_user_should_check="Check institution/account details and annual interest total.",
        evidence_expected=["bank interest statement"],
        confidence_level="medium",
    ),
    "managed_fund_annual_tax_statement": ExplanationTemplate(
        category="evidence_requirement",
        plain_english_summary="Managed fund annual tax statement required to support reported distribution.",
        why_it_matters="Managed fund distributions often include tax components that need statement support.",
        what_user_should_check="Upload the annual tax statement or tax summary from your managed fund or investment platform.",
        evidence_expected=["managed fund annual tax statement"],
        confidence_level="high",
    ),
    "managed_fund_capital_gains_schedule": ExplanationTemplate(
        category="evidence_requirement",
        plain_english_summary="Managed fund capital gains component needs supporting schedule details.",
        why_it_matters="Capital gains components from managed funds can affect downstream CGT treatment.",
        what_user_should_check="Upload the statement section showing managed fund capital gains and CGT components.",
        evidence_expected=["managed fund capital gains schedule"],
        confidence_level="high",
    ),
    "managed_fund_foreign_income_support": ExplanationTemplate(
        category="evidence_requirement",
        plain_english_summary="Managed fund foreign income component needs supporting statement details.",
        why_it_matters="Foreign income details may affect foreign tax paid or offset treatment.",
        what_user_should_check="Upload the statement section showing foreign income, foreign tax paid, or foreign tax offset details.",
        evidence_expected=["managed fund foreign income support"],
        confidence_level="high",
    ),
    "share_buy_contract_note": ExplanationTemplate(
        category="evidence_requirement",
        plain_english_summary="Share purchase records should be supported by a broker contract note.",
        why_it_matters="Purchase records help validate acquisition details and future cost-base treatment.",
        what_user_should_check="Upload the broker contract note or transaction confirmation for share purchases.",
        evidence_expected=["share buy contract note"],
        confidence_level="high",
    ),
    "share_sell_contract_note": ExplanationTemplate(
        category="evidence_requirement",
        plain_english_summary="Share disposal records should be supported by a broker contract note.",
        why_it_matters="Disposal records help validate sale proceeds, dates, and capital outcomes.",
        what_user_should_check="Upload the broker contract note or transaction confirmation for share sales.",
        evidence_expected=["share sell contract note"],
        confidence_level="high",
    ),
    "share_dividend_statement": ExplanationTemplate(
        category="evidence_requirement",
        plain_english_summary="Dividend income should be supported by a dividend or registry statement.",
        why_it_matters="Dividend statements help validate dividend amounts and franking credit details.",
        what_user_should_check="Upload the dividend statement, share registry statement, or annual tax statement showing dividends and franking credits.",
        evidence_expected=["share dividend statement"],
        confidence_level="high",
    ),
    "share_annual_broker_summary": ExplanationTemplate(
        category="evidence_requirement",
        plain_english_summary="An annual broker summary can help support your share activity across the year.",
        why_it_matters="Broker summaries help cross-check transactions and annual share activity totals.",
        what_user_should_check="Upload the annual broker report or transaction summary if available.",
        evidence_expected=["annual broker summary"],
        confidence_level="medium",
    ),
    "crypto_exchange_transaction_export": ExplanationTemplate(
        category="evidence_requirement",
        plain_english_summary="Crypto acquisition activity should be supported by an exchange transaction export.",
        why_it_matters="Exchange exports help validate crypto purchases, values, and transaction history.",
        what_user_should_check="Upload the CSV export, annual tax report, or transaction history from your crypto exchange.",
        evidence_expected=["crypto exchange transaction export"],
        confidence_level="high",
    ),
    "crypto_disposal_supporting_records": ExplanationTemplate(
        category="evidence_requirement",
        plain_english_summary="Crypto disposals need supporting records for proceeds, fees, and cost basis.",
        why_it_matters="Disposal records support capital gain or loss review and acquisition tracing.",
        what_user_should_check="Upload records showing crypto disposals, swaps, sales, fees, and acquisition cost basis.",
        evidence_expected=["crypto disposal supporting records"],
        confidence_level="high",
    ),
    "crypto_staking_income_statement": ExplanationTemplate(
        category="evidence_requirement",
        plain_english_summary="Crypto staking income should be supported by a platform or wallet report.",
        why_it_matters="Staking income reports help validate reward amounts and income dates.",
        what_user_should_check="Upload the exchange, wallet, or platform report showing staking rewards or crypto income.",
        evidence_expected=["crypto staking income statement"],
        confidence_level="high",
    ),
    "crypto_wallet_activity_export": ExplanationTemplate(
        category="evidence_requirement",
        plain_english_summary="A wallet activity export can help support your self-custody crypto history.",
        why_it_matters="Wallet exports help cross-check self-custody transactions that may not appear on exchange reports.",
        what_user_should_check="Upload wallet activity exports or transaction history for self-custody wallets if available.",
        evidence_expected=["crypto wallet activity export"],
        confidence_level="medium",
    ),
}


def _generic_template(category: str, target_type: str) -> ExplanationTemplate:
    if target_type == "evidence_obligation":
        return ExplanationTemplate(
            category="evidence_requirement",
            plain_english_summary="This evidence requirement was created and needs review.",
            why_it_matters="Supporting records improve confidence in your tax review package.",
            what_user_should_check="Check whether available documents align to this requirement.",
            evidence_expected=["supporting document"],
            confidence_level="low",
        )
    return ExplanationTemplate(
        category=category or "tax_item",
        plain_english_summary="This tax item was captured for review.",
        why_it_matters="Review helps confirm the item is complete and correctly categorized.",
        what_user_should_check="Check amount, date, and category alignment with your records.",
        evidence_expected=["supporting document"],
        confidence_level="low",
    )


def build_tax_item_explanation(
    *,
    target_type: str,
    target_id: str,
    category: str | None,
    source: str = "review",
    rule_version: str | None = None,
) -> dict:
    key = (category or "").strip().lower()
    template = TAX_CATEGORY_TEMPLATES.get(key) or _generic_template(key, target_type)
    return {
        "explanation_id": f"{target_type}:{target_id}",
        "target_type": target_type,
        "target_id": target_id,
        "category": template.category,
        "plain_english_summary": template.plain_english_summary,
        "why_it_matters": template.why_it_matters,
        "what_user_should_check": template.what_user_should_check,
        "evidence_expected": template.evidence_expected,
        "confidence_level": template.confidence_level,
        "rule_version": rule_version,
        "source": source,
    }


def build_evidence_obligation_explanation(
    *,
    target_id: str,
    obligation_key: str | None,
    obligation_category: str | None,
    rule_version: str | None,
    source: str = "rule",
) -> dict:
    key = (obligation_key or "").strip().lower()
    template = OBLIGATION_TEMPLATE_BY_KEY.get(key) or _generic_template(obligation_category or "evidence", "evidence_obligation")
    return {
        "explanation_id": f"evidence_obligation:{target_id}",
        "target_type": "evidence_obligation",
        "target_id": target_id,
        "category": template.category,
        "plain_english_summary": template.plain_english_summary,
        "why_it_matters": template.why_it_matters,
        "what_user_should_check": template.what_user_should_check,
        "evidence_expected": template.evidence_expected,
        "confidence_level": template.confidence_level,
        "rule_version": rule_version,
        "source": source,
    }
