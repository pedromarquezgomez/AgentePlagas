from typing import Any
from app.skills.contracts import ProductSkill
from app.skills.registry import default_skill_registry


class SkillsBuilder:
    def __init__(self, skill_registry: Any = None) -> None:
        self.skill_registry = skill_registry or default_skill_registry()

    def build(self) -> list[ProductSkill]:
        if not self.skill_registry:
            return []
        try:
            return self.skill_registry.list_skills()
        except Exception:
            return []
