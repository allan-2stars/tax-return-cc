import pathlib
import yaml
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


class CryptoSkillAU(TaxSkill):
    skill_id = _YAML["skill_id"]
    version = _YAML["version"]
    owned_categories = _YAML["owned_categories"]

    def should_activate(self, profile) -> bool:
        return bool(getattr(profile, "has_crypto", False))

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
        return "Crypto and digital assets are treated as capital gains events under Australian tax law."

    def extract_events(self, doc, classification) -> list:
        return []
