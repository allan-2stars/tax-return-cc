from app.skills.base import TaxSkill


class EmployeeTaxAU(TaxSkill):
    skill_id = "employee_tax_au"
    version = "1.0.0"
    owned_categories = [
        "payg_income",
        "allowance",
        "lump_sum",
        "work_expense",
        "vehicle",
        "travel",
        "uniform",
        "self_education",
        "other_deduction",
        "wfh_deduction",
    ]

    def should_activate(self, profile) -> bool:
        return True

    def get_questions(self, profile) -> list:
        raise NotImplementedError

    def get_evidence_requirements(self, profile) -> list:
        raise NotImplementedError

    def get_missing_evidence(self, profile, events) -> list:
        raise NotImplementedError

    def get_review_questions(self, event) -> list:
        raise NotImplementedError

    def get_risk_flags(self, events) -> list:
        raise NotImplementedError

    def explain(self, event) -> str:
        raise NotImplementedError

    def extract_events(self, doc, classification) -> list:
        raise NotImplementedError
