import pathlib
import re

import yaml

from app.ai.base import EventCandidate
from app.skills.base import (
    CalculationResult,
    EvidenceRequirement,
    MissingEvidence,
    Question,
    ReviewQuestion,
    RiskFlag,
    TaxSkill,
)

_SKILL_DIR = pathlib.Path(__file__).parent
with (_SKILL_DIR / "skill.yaml").open() as _f:
    _YAML = yaml.safe_load(_f)


def _clean_text(doc) -> str:
    text = getattr(doc, "extracted_text", None) or ""
    return text.replace("\r", "\n")


def _parse_number(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.replace(",", "").replace("$", "").strip()
    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def _parse_date(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw)
    if m:
        day, month, year = m.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    m = re.fullmatch(r"(\d{1,2})-([A-Za-z]{3})-(\d{4})", raw)
    if m:
        day, mon, year = m.groups()
        months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        month = months.get(mon.lower())
        if month:
            return f"{year}-{month:02d}-{int(day):02d}"
    m = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", raw)
    if m:
        day, mon, year = m.groups()
        months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        month = months.get(mon.lower())
        if month:
            return f"{year}-{month:02d}-{int(day):02d}"
    return None


def _extract_first(text: str, patterns: list[str], flags: int = re.IGNORECASE) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return match.group(1).strip()
    return None


def _extract_share_transaction(text: str, transaction_type: str) -> dict:
    stock_code = _extract_first(
        text,
        [
            r"\b(?:stock\s*code|security\s*code|code|symbol)\s*[:#-]?\s*([A-Z]{2,6})\b",
            r"\bASX\s*[:\-]?\s*([A-Z]{2,6})\b",
            r"\b([A-Z]{2,6})\s+(?:ORD|ETF|FPO)\b",
        ],
        flags=re.IGNORECASE,
    )
    if stock_code:
        stock_code = stock_code.upper()

    platform = _extract_first(
        text,
        [
            r"\b(?:broker|platform|participant)\s*[:\-]\s*([^\n]+)",
            r"\b(?:placed through|executed by)\s+([^\n]+)",
        ],
    )
    exchange = _extract_first(text, [r"\b(ASX|NYSE|NASDAQ|CBOE)\b"], flags=re.IGNORECASE)
    if exchange:
        exchange = exchange.upper()

    trade_date = _parse_date(
        _extract_first(
            text,
            [
                r"\b(?:trade\s*date|contract\s*date|date)\s*[:\-]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}-[A-Za-z]{3}-[0-9]{4}|[0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})",
            ],
        )
    )
    settlement_date = _parse_date(
        _extract_first(
            text,
            [
                r"\bsettlement\s*date\s*[:\-]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}-[A-Za-z]{3}-[0-9]{4}|[0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})",
            ],
        )
    )
    units = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:quantity|units|shares?)\s*[:\-]?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
                r"\b([0-9][0-9,]*(?:\.[0-9]+)?)\s+(?:shares?|units?)\b",
            ],
        )
    )
    price_per_unit = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:price\s*per\s*unit|price|at)\s*[:\-]?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )
    gross_amount = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:gross\s*(?:amount|consideration)|trade\s*value|contract\s*amount|consideration)\s*[:\-]?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )
    brokerage_fee = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:brokerage(?:\s*fee)?|fees?)\s*[:\-]?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )

    if gross_amount is None and units is not None and price_per_unit is not None:
        gross_amount = round(units * price_per_unit, 2)

    metadata = {
        "investment_sub_type": "shares",
        "transaction_type": transaction_type,
        "platform": platform,
        "stock_code": stock_code,
        "exchange": exchange,
        "trade_date": trade_date,
        "settlement_date": settlement_date,
        "units": units,
        "price_per_unit": price_per_unit,
        "gross_amount": gross_amount,
        "brokerage_fee": brokerage_fee,
    }
    return {k: v for k, v in metadata.items() if v is not None}


def _build_description(transaction_type: str, metadata: dict, fallback: str) -> str:
    stock_code = metadata.get("stock_code")
    units = metadata.get("units")
    price = metadata.get("price_per_unit")
    action = "Buy" if transaction_type == "buy" else "Sell"
    if stock_code and units is not None and price is not None:
        units_text = int(units) if float(units).is_integer() else units
        return f"Shares {action}: {units_text} × {stock_code} @ ${float(price):.2f}"
    if stock_code:
        return f"Shares {action}: {stock_code}"
    return fallback


def _extract_dividend_statement(text: str) -> dict:
    company_name = _extract_first(
        text,
        [
            r"\b(?:company\s*name|company|issuer)\s*[:\-]\s*([^\n]+)",
            r"^\s*([A-Z][A-Za-z0-9&.,'() /-]*(?:Limited|Ltd|Group Limited|Corporation|Holdings Limited|PLC))\s*$",
        ],
        flags=re.IGNORECASE | re.MULTILINE,
    )
    stock_code = _extract_first(
        text,
        [
            r"\b(?:stock\s*code|security\s*code|asx\s*code|ticker|symbol)\s*[:#-]?\s*([A-Z]{2,6})\b",
            r"\(([A-Z]{2,6})\)",
        ],
        flags=re.IGNORECASE,
    )
    if stock_code:
        stock_code = stock_code.upper()

    dividend_amount = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:dividend(?:\s*amount)?|net\s*dividend)\s*[:\-]?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )
    franking_credits = _parse_number(
        _extract_first(
            text,
            [
                r"\bfranking\s*credits?\s*[:\-]?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )
    payment_date = _parse_date(
        _extract_first(
            text,
            [
                r"\bpayment\s*date\s*[:\-]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}-[A-Za-z]{3}-[0-9]{4}|[0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})",
            ],
        )
    )
    record_date = _parse_date(
        _extract_first(
            text,
            [
                r"\brecord\s*date\s*[:\-]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}-[A-Za-z]{3}-[0-9]{4}|[0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})",
            ],
        )
    )
    shares_held = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:shares?\s*held|holding|units?\s*held)\s*[:\-]?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )
    currency = _extract_first(
        text,
        [
            r"\bcurrency\s*[:\-]\s*([A-Z]{3})\b",
            r"\b(AUD|USD|NZD|GBP|EUR)\b",
        ],
        flags=re.IGNORECASE,
    )
    if currency:
        currency = currency.upper()

    metadata = {
        "investment_sub_type": "shares",
        "transaction_type": "dividend",
        "income_type": "dividend",
        "company_name": company_name,
        "stock_code": stock_code,
        "dividend_amount": dividend_amount,
        "franking_credits": franking_credits,
        "payment_date": payment_date,
        "record_date": record_date,
        "shares_held": shares_held,
        "currency": currency,
    }
    return {k: v for k, v in metadata.items() if v is not None}


def _build_dividend_description(metadata: dict, fallback: str) -> str:
    company_name = metadata.get("company_name")
    stock_code = metadata.get("stock_code")
    if company_name and stock_code:
        return f"Dividend: {company_name} ({stock_code})"
    if company_name:
        return f"Dividend: {company_name}"
    if stock_code:
        return f"Dividend: {stock_code}"
    return fallback


def _extract_share_annual_summary(text: str) -> dict:
    broker_name = _extract_first(
        text,
        [
            r"\b(?:broker|broker\s*name|platform)\s*[:\-]\s*([^\n]+)",
        ],
    )
    financial_year = _extract_first(
        text,
        [
            r"\bfinancial\s*year\s*[:\-]\s*([0-9]{4}-[0-9]{2}|[0-9]{4}/[0-9]{4})",
            r"\bfy\s*[:\-]\s*([0-9]{4}-[0-9]{2}|[0-9]{4}/[0-9]{4})",
        ],
        flags=re.IGNORECASE,
    )
    total_buy_transactions = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:buy|purchase)\s*transactions?\s*[:\-]?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )
    total_sell_transactions = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:sell|sale)\s*transactions?\s*[:\-]?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )
    total_purchase_value = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:purchases?|purchase\s*value|total\s*purchases?)\s*[:\-]?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )
    total_sale_value = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:sales?|sale\s*value|total\s*sales?)\s*[:\-]?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )
    total_dividend_income = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:dividends?|dividend\s*income|total\s*dividends?)\s*[:\-]?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )
    total_brokerage_fees = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:brokerage|brokerage\s*fees|fees?)\s*[:\-]?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )
    reported_holdings_count = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:holdings?\s*count|reported\s*holdings?|holdings?)\s*[:\-]?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )

    metadata = {
        "investment_sub_type": "shares",
        "transaction_type": "annual_summary",
        "broker_name": broker_name,
        "financial_year": financial_year,
        "total_buy_transactions": total_buy_transactions,
        "total_sell_transactions": total_sell_transactions,
        "total_purchase_value": total_purchase_value,
        "total_sale_value": total_sale_value,
        "total_dividend_income": total_dividend_income,
        "total_brokerage_fees": total_brokerage_fees,
        "reported_holdings_count": reported_holdings_count,
    }
    return {k: v for k, v in metadata.items() if v is not None}


def _build_share_annual_summary_description(metadata: dict, fallback: str) -> str:
    broker_name = metadata.get("broker_name")
    financial_year = metadata.get("financial_year")
    if broker_name and financial_year:
        return f"Share Annual Summary: {broker_name} ({financial_year})"
    if broker_name:
        return f"Share Annual Summary: {broker_name}"
    if financial_year:
        return f"Share Annual Summary ({financial_year})"
    return fallback


def _extract_managed_fund_statement(text: str) -> dict:
    fund_name = _extract_first(
        text,
        [
            r"\b(?:fund\s*name|investment\s*name)\s*[:\-]\s*([^\n]+)",
            r"^\s*([A-Z][A-Za-z0-9&.,'() /-]*Fund(?:\s+[A-Z][A-Za-z0-9&.,'() /-]*)?)\s*$",
        ],
        flags=re.IGNORECASE | re.MULTILINE,
    )
    fund_manager = _extract_first(
        text,
        [
            r"\b(?:fund\s*manager|manager|issuer|responsible\s*entity)\s*[:\-]\s*([^\n]+)",
        ],
    )
    distribution_amount = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:distribution|distribution\s*amount|total\s*distribution)\s*[:\-]?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )
    capital_gains_component = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:capital\s*gains?|capital\s*gains?\s*component)\s*[:\-]?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )
    foreign_income_component = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:foreign\s*income|foreign\s*income\s*component)\s*[:\-]?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )
    tfn_withholding = _parse_number(
        _extract_first(
            text,
            [
                r"\b(?:tfn\s*withholding|tax\s*file\s*number\s*withholding)\s*[:\-]?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            ],
        )
    )
    statement_date = _parse_date(
        _extract_first(
            text,
            [
                r"\b(?:statement\s*date|distribution\s*date|date)\s*[:\-]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}-[A-Za-z]{3}-[0-9]{4}|[0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})",
            ],
        )
    )
    financial_year = _extract_first(
        text,
        [
            r"\bfinancial\s*year\s*[:\-]\s*([0-9]{4}-[0-9]{2}|[0-9]{4}/[0-9]{4})",
            r"\bfor\s+the\s+year\s+ended\s+([0-9]{4}-[0-9]{2})",
        ],
        flags=re.IGNORECASE,
    )

    metadata = {
        "investment_sub_type": "managed_fund",
        "income_type": "managed_fund_distribution",
        "fund_name": fund_name,
        "fund_manager": fund_manager,
        "distribution_amount": distribution_amount,
        "capital_gains_component": capital_gains_component,
        "foreign_income_component": foreign_income_component,
        "tfn_withholding": tfn_withholding,
        "statement_date": statement_date,
        "financial_year": financial_year,
    }
    return {k: v for k, v in metadata.items() if v is not None}


def _build_managed_fund_description(metadata: dict, fallback: str) -> str:
    fund_name = metadata.get("fund_name")
    if fund_name:
        return f"Managed Fund Distribution: {fund_name}"
    return fallback


class InvestmentSkill(TaxSkill):
    skill_id = _YAML["skill_id"]
    version = _YAML["version"]
    owned_categories = _YAML["owned_categories"]

    def should_activate(self, profile) -> bool:
        return bool(getattr(profile, "has_investments", False) or getattr(profile, "has_crypto", False))

    def get_questions(self, profile) -> list[Question]:
        return []

    def get_evidence_requirements(self, profile) -> list[EvidenceRequirement]:
        return []

    def get_missing_evidence(self, profile, events) -> list[MissingEvidence]:
        return []

    def get_review_questions(self, event) -> list[ReviewQuestion]:
        return []

    def get_risk_flags(self, events: list) -> list[RiskFlag]:
        return []

    def explain(self, event) -> str:
        return "Investment transactions need review before they can be relied on for tax outcomes."

    def extract_events(self, doc, classification) -> list[EventCandidate]:
        doc_type = classification.document_type
        if doc_type == "share_annual_broker_summary":
            metadata = _extract_share_annual_summary(_clean_text(doc))
            meaningful_fields = {
                key: value
                for key, value in metadata.items()
                if key not in {"investment_sub_type", "transaction_type"}
            }
            if not meaningful_fields:
                return []

            core_fields = [
                metadata.get("broker_name"),
                metadata.get("financial_year"),
                metadata.get("total_purchase_value"),
                metadata.get("total_sale_value"),
                metadata.get("total_dividend_income"),
                metadata.get("total_brokerage_fees"),
            ]
            confidence = 0.6
            if metadata.get("broker_name") and metadata.get("financial_year") and any(
                metadata.get(key) is not None
                for key in {"total_purchase_value", "total_sale_value", "total_dividend_income"}
            ):
                confidence = 0.9
            elif any(value is not None for value in core_fields):
                confidence = 0.7

            amount = (
                metadata.get("total_dividend_income")
                if metadata.get("total_dividend_income") is not None
                else metadata.get("total_sale_value")
                if metadata.get("total_sale_value") is not None
                else metadata.get("total_purchase_value")
            )

            return [
                EventCandidate(
                    event_type="investment",
                    category="share_annual_summary",
                    description=_build_share_annual_summary_description(
                        metadata,
                        getattr(doc, "original_filename", "") or "Share annual broker summary",
                    ),
                    amount=amount,
                    date=None,
                    confidence=confidence,
                    ai_reasoning=(
                        "Broker annual summary fields were extracted from document text."
                        if confidence >= 0.9
                        else "Partial broker annual summary fields were extracted; user review is required."
                    ),
                    metadata=metadata,
                )
            ]

        if doc_type == "managed_fund_annual_tax_statement":
            metadata = _extract_managed_fund_statement(_clean_text(doc))
            meaningful_fields = {
                key: value
                for key, value in metadata.items()
                if key not in {"investment_sub_type", "income_type"}
            }
            if not meaningful_fields:
                return []

            core_fields = [
                metadata.get("fund_name"),
                metadata.get("distribution_amount"),
                metadata.get("statement_date"),
                metadata.get("capital_gains_component"),
                metadata.get("foreign_income_component"),
                metadata.get("tfn_withholding"),
            ]
            confidence = 0.6
            if metadata.get("distribution_amount") is not None and metadata.get("fund_name"):
                confidence = 0.9
            elif any(value is not None for value in core_fields):
                confidence = 0.7

            return [
                EventCandidate(
                    event_type="investment",
                    category="managed_fund_distribution",
                    description=_build_managed_fund_description(
                        metadata,
                        getattr(doc, "original_filename", "") or "Managed fund annual statement",
                    ),
                    amount=metadata.get("distribution_amount"),
                    date=metadata.get("statement_date"),
                    confidence=confidence,
                    ai_reasoning=(
                        "Managed fund statement fields were extracted from document text."
                        if confidence >= 0.9
                        else "Partial managed fund statement fields were extracted; user review is required."
                    ),
                    metadata=metadata,
                )
            ]

        if doc_type == "share_dividend_statement":
            metadata = _extract_dividend_statement(_clean_text(doc))
            meaningful_fields = {
                key: value
                for key, value in metadata.items()
                if key not in {"investment_sub_type", "transaction_type", "income_type"}
            }
            if not meaningful_fields:
                return []

            core_fields = [
                metadata.get("company_name"),
                metadata.get("stock_code"),
                metadata.get("dividend_amount"),
                metadata.get("payment_date"),
                metadata.get("franking_credits"),
            ]
            confidence = 0.6
            if metadata.get("dividend_amount") is not None and (
                metadata.get("company_name") or metadata.get("stock_code")
            ):
                confidence = 0.9
            elif any(value is not None for value in core_fields):
                confidence = 0.7

            return [
                EventCandidate(
                    event_type="investment",
                    category="dividend",
                    description=_build_dividend_description(
                        metadata,
                        getattr(doc, "original_filename", "") or "Dividend statement",
                    ),
                    amount=metadata.get("dividend_amount"),
                    date=metadata.get("payment_date") or metadata.get("record_date"),
                    confidence=confidence,
                    ai_reasoning=(
                        "Dividend statement fields were extracted from document text."
                        if confidence >= 0.9
                        else "Partial dividend statement fields were extracted; user review is required."
                    ),
                    metadata=metadata,
                )
            ]

        if doc_type not in {"share_buy_contract_note", "share_sell_contract_note"}:
            return []

        transaction_type = "buy" if doc_type == "share_buy_contract_note" else "sell"
        metadata = _extract_share_transaction(_clean_text(doc), transaction_type)
        meaningful_fields = {
            key: value
            for key, value in metadata.items()
            if key not in {"investment_sub_type", "transaction_type"}
        }
        if not meaningful_fields:
            return []

        gross_amount = metadata.get("gross_amount")
        brokerage_fee = metadata.get("brokerage_fee")
        amount = gross_amount
        if gross_amount is not None and brokerage_fee is not None:
            if transaction_type == "buy":
                amount = round(float(gross_amount) + float(brokerage_fee), 2)
            else:
                amount = round(float(gross_amount) - float(brokerage_fee), 2)

        core_fields = [
            metadata.get("stock_code"),
            metadata.get("units"),
            metadata.get("price_per_unit"),
            metadata.get("gross_amount"),
            metadata.get("trade_date"),
        ]
        confidence = 0.6
        if metadata.get("stock_code") and metadata.get("units") is not None and (
            metadata.get("price_per_unit") is not None or metadata.get("gross_amount") is not None
        ):
            confidence = 0.9
        elif any(value is not None for value in core_fields):
            confidence = 0.7

        category = "shares_acquisition" if transaction_type == "buy" else "capital_gain_candidate"
        reasoning = (
            "Share contract note fields were extracted from document text."
            if confidence >= 0.9
            else "Partial share contract note fields were extracted; user review is required."
        )

        return [
            EventCandidate(
                event_type="investment",
                category=category,
                description=_build_description(
                    transaction_type,
                    metadata,
                    getattr(doc, "original_filename", "") or "Share contract note",
                ),
                amount=amount,
                date=metadata.get("trade_date") or metadata.get("settlement_date"),
                confidence=confidence,
                ai_reasoning=reasoning,
                metadata=metadata,
            )
        ]

    def calculate(self, event) -> CalculationResult | None:
        return None
