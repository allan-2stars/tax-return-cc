import logging

from app.skills.base import TaxSkill


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, TaxSkill] = {}

    def register(self, skill: TaxSkill) -> None:
        for cat in skill.owned_categories:
            for existing in self._skills.values():
                if cat in existing.owned_categories:
                    logging.getLogger(__name__).warning(
                        "Category conflict: %s claimed by %s and %s",
                        cat,
                        existing.skill_id,
                        skill.skill_id,
                    )
        self._skills[skill.skill_id] = skill

    def get(self, skill_id: str) -> TaxSkill | None:
        return self._skills.get(skill_id)

    def active_for_profile(self, profile) -> list[TaxSkill]:
        return [s for s in self._skills.values() if s.should_activate(profile)]
