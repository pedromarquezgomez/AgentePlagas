import logging
from app.config.agent_loader import AgentConfigLoader
from app.diagnostics.contracts import DiagnosisAssessment

logger = logging.getLogger(__name__)

class QuestionGenerator:
    def __init__(self, loader: AgentConfigLoader | None = None) -> None:
        self.loader = loader or AgentConfigLoader()

    def generate_question(self, assessment: DiagnosisAssessment) -> str:
        templates = self.loader.load_response_templates()
        
        def get_template(section: str, key: str, fallback: str) -> str:
            val = templates.get(section, {}).get(key, {}).get("es")
            return val if val is not None else fallback

        if assessment.knowledge_key == "plant_pests":
            return get_template(
                "diagnosis",
                "plant_pest_ambiguous",
                "Podría tratarse de pulgón verde, cochinilla o chinche verde. ¿Los ves agrupados en brotes tiernos o debajo de las hojas? ¿Notas hojas pegajosas o brillantes?"
            )
        
        # Fallback genérico para plaga desconocida
        return get_template(
            "diagnosis",
            "unknown_pest",
            "Para orientarte mejor necesito algún detalle: ¿son pequeños o grandes? ¿Vuelan, saltan o permanecen quietos?"
        )
