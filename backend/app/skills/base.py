from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Question:
    id: str
    ask: str
    type: str                                  # single_choice | multi_choice | text | number
    options: list[str] | None = None
    branches: dict[str, list[str]] | None = None   # option_value → [question_ids to insert]
    trigger: str | None = None                 # optional condition string
    required: bool = True                      # False → show skip button in UI
    why: str | None = None                     # shown in "Why do we ask?" tooltip
    hint: str | None = None                    # shown as sub-text below question
    currency: bool = False                     # True → render $ prefix input in UI


@dataclass
class EvidenceRequirement:
    id: str
    display: str
    weight: int
    available_after_fy: bool = False
    available_from: str = "anytime"            # anytime | july | august | etc.
    condition: str | None = None               # e.g. "has_wfh", "has_private_health"
    required: bool = False
    covers_category: str | None = None         # TaxEvent category that satisfies this req


@dataclass
class MissingEvidence:
    requirement_id: str
    display: str
    weight: int
    skill_id: str
    how_to_get: str = ""
    available_after_fy: bool = False           # mirrors EvidenceRequirement.available_after_fy


@dataclass
class ReviewQuestion:
    id: str
    ask: str
    type: str = "text"                         # text | single_choice | number
    options: list[str] | None = None


@dataclass
class RiskFlag:
    id: str
    risk_level: str                            # low | medium | high
    message: str
    event_id: str | None = None


@dataclass
class CalculationResult:
    amount: float
    method: str
    breakdown: dict = field(default_factory=dict)


class TaxSkill(ABC):
    skill_id: str
    version: str
    owned_categories: list[str]

    @abstractmethod
    def should_activate(self, profile) -> bool: ...

    @abstractmethod
    def get_questions(self, profile) -> list[Question]: ...

    @abstractmethod
    def get_evidence_requirements(self, profile) -> list[EvidenceRequirement]: ...

    @abstractmethod
    def get_missing_evidence(self, profile, events) -> list[MissingEvidence]: ...

    @abstractmethod
    def get_review_questions(self, event) -> list[ReviewQuestion]: ...

    @abstractmethod
    def get_risk_flags(self, events: list) -> list[RiskFlag]: ...

    @abstractmethod
    def explain(self, event) -> str: ...

    @abstractmethod
    def extract_events(self, doc, classification) -> list: ...

    def calculate(self, event) -> CalculationResult | None:
        return None
