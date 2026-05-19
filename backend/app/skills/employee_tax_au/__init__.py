import pathlib

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

# Map category → event_type for extract_events
_CATEGORY_EVENT_TYPE: dict[str, str] = {
    "payg_income": "income",
    "allowance": "income",
    "lump_sum": "income",
    "bank_interest": "income",
    "investment_income_basic": "income",
    "wfh_deduction": "wfh",
    "work_expense": "deduction",
    "work_subscription": "deduction",
    "work_equipment": "deduction",
    "vehicle": "deduction",
    "travel": "deduction",
    "uniform": "deduction",
    "self_education": "deduction",
    "other_deduction": "deduction",
    "donation": "deduction",
    "private_health_rebate": "deduction",
}

# Map requirement_id → the category it "covers"
_REQ_COVERS: dict[str, str] = {
    "payg_summary": "payg_income",
    "bank_interest_statement": "bank_interest",
    "wfh_diary": "wfh_deduction",
    "private_health_statement": "private_health_rebate",
    "work_receipts": "work_expense",
}

# Per-category review questions surfaced on Review Cards
_REVIEW_QUESTIONS: dict[str, list[ReviewQuestion]] = {
    "work_expense": [
        ReviewQuestion(
            id="work_purpose",
            ask="Was this expense exclusively for work?",
            type="single_choice",
            options=["yes", "no", "partially"],
        ),
    ],
    "work_subscription": [
        ReviewQuestion(
            id="subscription_work_purpose",
            ask="Is this subscription used exclusively for work?",
            type="single_choice",
            options=["yes", "no", "partially"],
        ),
    ],
    "work_equipment": [
        ReviewQuestion(
            id="equipment_work_purpose",
            ask="Is this equipment used exclusively for work?",
            type="single_choice",
            options=["yes", "no", "partially"],
        ),
    ],
    "wfh_deduction": [
        ReviewQuestion(
            id="wfh_method",
            ask="Which WFH calculation method are you using?",
            type="single_choice",
            options=["fixed_rate", "actual_cost"],
        ),
    ],
    "self_education": [
        ReviewQuestion(
            id="work_connection",
            ask="How does this course directly connect to your current role?",
            type="text",
        ),
    ],
    "vehicle": [
        ReviewQuestion(
            id="vehicle_method",
            ask="Which vehicle claim method are you using?",
            type="single_choice",
            options=["cents_per_km", "logbook"],
        ),
    ],
}

_DEFAULT_REVIEW_QUESTIONS = [
    ReviewQuestion(
        id="confirm_purpose",
        ask="Please confirm the work-related purpose of this item.",
        type="text",
    ),
]


class EmployeeTaxAU(TaxSkill):
    skill_id = _YAML["skill_id"]
    version = _YAML["version"]
    owned_categories: list[str] = _YAML["owned_categories"]

    # ── activation ────────────────────────────────────────────────────────────

    def should_activate(self, profile) -> bool:
        employment_type = getattr(profile, "employment_type", None)
        return employment_type not in ("sole_trader",)

    # ── questions (for Interview Engine) ─────────────────────────────────────

    def get_questions(self, profile) -> list[Question]:
        return [
            Question(
                id=q["id"],
                ask=q["ask"],
                type=q["type"],
                options=q.get("options"),
                branches=q.get("branches"),
            )
            for q in _YAML.get("questions", [])
        ]

    # ── evidence requirements ─────────────────────────────────────────────────

    def get_evidence_requirements(self, profile) -> list[EvidenceRequirement]:
        return [
            EvidenceRequirement(
                id=r["id"],
                display=r["display"],
                weight=r["weight"],
                available_after_fy=r.get("available_after_fy", False),
                available_from=r.get("available_from", "anytime"),
                condition=r.get("condition"),
                required=r.get("required", False),
            )
            for r in _YAML.get("evidence_requirements", [])
        ]

    # ── missing evidence ──────────────────────────────────────────────────────

    def get_missing_evidence(self, profile, events) -> list[MissingEvidence]:
        requirements = self.get_evidence_requirements(profile)
        covered_categories = {getattr(e, "category", None) for e in events}

        missing = []
        for req in requirements:
            # Skip if profile condition is not met
            if req.condition:
                if not getattr(profile, req.condition, False):
                    continue

            # Skip if this requirement is already covered by an existing event
            covered_by = _REQ_COVERS.get(req.id)
            if covered_by and covered_by in covered_categories:
                continue

            missing.append(
                MissingEvidence(
                    requirement_id=req.id,
                    display=req.display,
                    weight=req.weight,
                    skill_id=self.skill_id,
                )
            )
        return missing

    # ── review questions (for Review Cards) ──────────────────────────────────

    def get_review_questions(self, event) -> list[ReviewQuestion]:
        category = getattr(event, "category", "")
        return _REVIEW_QUESTIONS.get(category, _DEFAULT_REVIEW_QUESTIONS)

    # ── risk flags ────────────────────────────────────────────────────────────

    def get_risk_flags(self, events: list) -> list[RiskFlag]:
        flags = []
        categories = [getattr(e, "category", None) for e in events]

        if "wfh_deduction" in categories:
            flags.append(RiskFlag(
                id="wfh_no_diary",
                risk_level="high",
                message="ATO requires records of hours worked from home",
            ))

        if "self_education" in categories:
            flags.append(RiskFlag(
                id="self_ed_no_connection",
                risk_level="medium",
                message="Self-education must connect to your current job",
            ))

        return flags

    # ── explanation ───────────────────────────────────────────────────────────

    def explain(self, event) -> str:
        templates = _YAML.get("explanation_templates", {})
        category = getattr(event, "category", "")
        return templates.get(category, templates.get("default", "This item needs review."))

    # ── event extraction ──────────────────────────────────────────────────────

    def extract_events(self, doc, classification) -> list[EventCandidate]:
        category = classification.suggested_category or "other_deduction"
        event_type = _CATEGORY_EVENT_TYPE.get(category, "deduction")
        notes = classification.notes or ""

        amounts = classification.extracted_amounts or []
        if amounts:
            return [
                EventCandidate(
                    event_type=event_type,
                    category=category,
                    description=a.get("description") or getattr(doc, "original_filename", "") or "",
                    amount=a.get("amount"),
                    date=a.get("date"),
                    confidence=classification.confidence,
                    ai_reasoning=notes,
                )
                for a in amounts
            ]

        return [
            EventCandidate(
                event_type=event_type,
                category=category,
                description=getattr(doc, "original_filename", "") or "",
                amount=None,
                date=None,
                confidence=classification.confidence,
                ai_reasoning=notes,
            )
        ]
