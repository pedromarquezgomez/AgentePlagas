import os
import logging
import yaml
from app.config.settings import settings

logger = logging.getLogger(__name__)

class AgentConfigLoader:
    _cache = {}

    def __init__(self, cache_enabled: bool | None = None) -> None:
        if cache_enabled is not None:
            self.cache_enabled = cache_enabled
        else:
            # Recuperar de settings de la app
            self.cache_enabled = getattr(settings, "agent_config_cache_enabled", True)

    def _read_file(self, relative_path: str, fallback: str = "") -> str:
        # Resolver ruta absoluta relativa al directorio de este archivo
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "prompts"))
        full_path = os.path.join(base_dir, relative_path)

        if self.cache_enabled and full_path in self._cache:
            return self._cache[full_path]

        if not os.path.exists(full_path):
            logger.warning("Falta archivo de prompt crítico: %s. Usando fallback.", relative_path)
            return fallback

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
                if self.cache_enabled:
                    self._cache[full_path] = content
                return content
        except Exception as exc:
            logger.error("Error leyendo archivo de prompt %s: %s. Usando fallback.", relative_path, exc)
            return fallback

    def load_system_prompt(self) -> str:
        fallback = (
            "Eres Hermes, asistente de control de plagas. Responde en español, "
            "no inventes datos, no ejecutes acciones sin validación y solicita "
            "aclaraciones cuando falte información esencial."
        )
        return self._read_file("system_prompt.md", fallback=fallback)

    def load_personality(self) -> str:
        return self._read_file("personality.md", fallback="")

    def load_conversation_rules(self) -> str:
        return self._read_file("conversation_rules.md", fallback="")

    def load_intake_policy(self) -> str:
        return self._read_file("intake_policy.md", fallback="")

    def load_recurrence_policy(self) -> str:
        return self._read_file("recurrence_policy.md", fallback="")

    def load_technical_diagnosis(self) -> str:
        return self._read_file("technical_diagnosis.md", fallback="")

    def load_response_style(self) -> str:
        return self._read_file("response_style.md", fallback="")

    def load_pest_knowledge(self, key: str) -> str:
        filename = f"{key}.md"
        relative_path = os.path.join("pest_knowledge", filename)
        return self._read_file(relative_path, fallback="")

    def load_response_templates(self) -> dict:
        yaml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "response_templates.yaml"))

        if self.cache_enabled and yaml_path in self._cache:
            return self._cache[yaml_path]

        if not os.path.exists(yaml_path):
            logger.warning("Falta archivo crítico de plantillas response_templates.yaml. Usando fallback vacío.")
            return {}

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                result = content if isinstance(content, dict) else {}
                if self.cache_enabled:
                    self._cache[yaml_path] = result
                return result
        except Exception as exc:
            logger.error("Error leyendo/parseando response_templates.yaml: %s. Usando fallback vacío.", exc)
            return {}

    def build_llm_prompt_sections(self, knowledge_key: str | None = None) -> str:
        sections = [
            "Return only strict JSON compatible with AgentResponse.",
            self.load_system_prompt(),
            self.load_personality(),
            self.load_conversation_rules(),
            self.load_intake_policy(),
            self.load_recurrence_policy(),
            self.load_technical_diagnosis(),
            self.load_response_style(),
        ]

        if knowledge_key:
            knowledge = self.load_pest_knowledge(knowledge_key)
            if knowledge:
                sections.append(f"# Pest Knowledge: {knowledge_key}\n{knowledge}")

        # Filtrar secciones vacías y unir con doble salto de línea
        return "\n\n".join(section.strip() for section in sections if section and section.strip())
