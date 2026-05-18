from abc import ABC, abstractmethod


class TaxSkill(ABC):
    skill_id: str
    version: str
    owned_categories: list[str]

    @abstractmethod
    def should_activate(self, profile) -> bool: ...

    @abstractmethod
    def get_questions(self, profile) -> list: ...

    @abstractmethod
    def get_evidence_requirements(self, profile) -> list: ...

    @abstractmethod
    def get_missing_evidence(self, profile, events) -> list: ...

    @abstractmethod
    def get_review_questions(self, event) -> list: ...

    @abstractmethod
    def get_risk_flags(self, events) -> list: ...

    @abstractmethod
    def explain(self, event) -> str: ...

    @abstractmethod
    def extract_events(self, doc, classification) -> list: ...

    def calculate(self, event):
        return None
