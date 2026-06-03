from app.skills.contracts import ProductSkill
from app.skills.definitions.default import DEFAULT_PRODUCT_SKILLS


class SkillRegistry:
    def __init__(self, skills: list[ProductSkill] | None = None) -> None:
        self._skills = {skill.name: skill for skill in (skills or DEFAULT_PRODUCT_SKILLS)}

    def list_skills(self) -> list[ProductSkill]:
        return list(self._skills.values())

    def get_skill(self, name: str) -> ProductSkill | None:
        return self._skills.get(name)

    def require_skill(self, name: str) -> ProductSkill:
        skill = self.get_skill(name)
        if skill is None:
            raise KeyError(f"Unknown product skill: {name}")
        return skill

    def prompt_sections(self) -> list[str]:
        return [skill.as_prompt_section() for skill in self.list_skills()]


def default_skill_registry() -> SkillRegistry:
    return SkillRegistry()
