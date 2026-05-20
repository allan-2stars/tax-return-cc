from dataclasses import dataclass
from decimal import Decimal

_ATO_CALCULATOR_URL = "https://www.ato.gov.au/calculators-and-tools"

_DISCLAIMER = (
    "These figures are based on confirmed items only and are provided to help you "
    "understand your tax position. They do not constitute tax advice. "
    "Please copy these figures to the ATO Income Tax Estimator and discuss with "
    "a registered tax agent before lodging."
)


@dataclass
class TaxSummary:
    gross_income:       Decimal
    total_deductions:   Decimal
    taxable_income:     Decimal
    payg_withheld:      Decimal
    confirmed_only:     bool
    pending_count:      int
    ato_calculator_url: str
    disclaimer:         str


class TaxEstimator:

    async def get_summary(self, workspace_id: str, db) -> TaxSummary:
        from app.repositories import events as events_repo

        all_events = await events_repo.get_by_workspace(db, workspace_id)

        confirmed = [e for e in all_events if e.status == "confirmed"]
        pending = [e for e in all_events if e.status != "confirmed"]

        gross_income = Decimal(0)
        total_deductions = Decimal(0)
        payg_withheld = Decimal(0)

        for ev in confirmed:
            amount = Decimal(str(ev.amount or 0))
            if ev.event_type == "income":
                gross_income += amount
                if ev.category == "payg_withheld":
                    payg_withheld += amount
            elif ev.event_type in ("deduction", "wfh"):
                total_deductions += amount

        taxable_income = gross_income - total_deductions

        return TaxSummary(
            gross_income=gross_income,
            total_deductions=total_deductions,
            taxable_income=taxable_income,
            payg_withheld=payg_withheld,
            confirmed_only=True,
            pending_count=len(pending),
            ato_calculator_url=_ATO_CALCULATOR_URL,
            disclaimer=_DISCLAIMER,
        )
