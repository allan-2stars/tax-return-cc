import asyncio
import logging

from app.skills.base import TaxSkill

logger = logging.getLogger(__name__)


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, TaxSkill] = {}

    def register(self, skill: TaxSkill, workspace_id: str | None = None) -> None:
        all_skills = list(self._skills.values()) + [skill]
        self._resolve_conflicts(all_skills, workspace_id)
        self._skills[skill.skill_id] = skill

    def _resolve_conflicts(
        self, skills: list[TaxSkill], workspace_id: str | None = None
    ) -> None:
        from app.repositories import audit as audit_repo

        seen: dict[str, str] = {}  # category → first-claiming skill_id
        for skill in skills:
            for cat in (skill.owned_categories or []):
                if cat in seen and seen[cat] != skill.skill_id:
                    existing_id = seen[cat]
                    logger.warning(
                        "Skill conflict: %s and %s both claim category %s",
                        existing_id,
                        skill.skill_id,
                        cat,
                    )
                    if workspace_id:
                        try:
                            asyncio.get_running_loop().create_task(
                                audit_repo.log_skill_conflict(
                                    workspace_id, cat, existing_id, skill.skill_id
                                )
                            )
                        except RuntimeError:
                            pass  # no running event loop (module init context)
                else:
                    seen[cat] = skill.skill_id

    # ── public query methods ──────────────────────────────────────────────────

    def load_for_profile(self, profile) -> list[TaxSkill]:
        return [s for s in self._skills.values() if s.should_activate(profile)]

    def get(self, skill_id: str) -> TaxSkill | None:
        return self._skills.get(skill_id)

    def get_owner(self, category: str) -> TaxSkill | None:
        for skill in self._skills.values():
            if category in (skill.owned_categories or []):
                return skill
        return None

    def check_activation_delta(
        self, answers: dict, current_skills: list[TaxSkill]
    ) -> list[TaxSkill]:
        """Return skills that would newly activate given answers dict."""
        current_ids = {s.skill_id for s in current_skills}

        class _ProfileLike:
            def __init__(self, data: dict) -> None:
                for k, v in data.items():
                    setattr(self, k, v)

        profile = _ProfileLike(answers)
        return [
            s for s in self._skills.values()
            if s.skill_id not in current_ids and s.should_activate(profile)
        ]


# ── module-level singleton ────────────────────────────────────────────────────

_registry = SkillRegistry()


def get_registry() -> SkillRegistry:
    return _registry


def _bootstrap() -> None:
    from app.skills.employee_tax_au import EmployeeTaxAU
    from app.skills.crypto_skill_au import CryptoSkillAU
    _registry.register(EmployeeTaxAU())
    _registry.register(CryptoSkillAU())


_bootstrap()
