import os
import logging
from app.skills.contracts import ProductSkill

logger = logging.getLogger(__name__)


def load_skills_from_disk() -> list[ProductSkill]:
    skills = []
    definitions_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "definitions"))
    
    if not os.path.exists(definitions_dir):
        logger.warning("El directorio de definiciones de skills no existe: %s", definitions_dir)
        return skills

    # Listar directorios y cargar SKILL.md
    for entry in sorted(os.listdir(definitions_dir)):
        entry_path = os.path.join(definitions_dir, entry)
        if os.path.isdir(entry_path):
            skill_file = os.path.join(entry_path, "SKILL.md")
            if os.path.exists(skill_file):
                try:
                    skill = ProductSkill.from_markdown_file(skill_file)
                    skills.append(skill)
                except Exception as exc:
                    logger.error("Error al cargar skill desde %s: %s", skill_file, exc)
    return skills


class SkillRegistry:
    def __init__(self, skills: list[ProductSkill] | None = None) -> None:
        if skills is None:
            skills = load_skills_from_disk()
        self._skills = {skill.name: skill for skill in skills}

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

