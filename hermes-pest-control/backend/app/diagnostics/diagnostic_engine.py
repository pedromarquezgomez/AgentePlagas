import logging
from typing import Any
from app.diagnostics.contracts import DiagnosisAssessment, DiagnosisState, DiagnosisHypothesis

logger = logging.getLogger(__name__)

class SemanticDiagnosisClassifier:
    async def classify(self, text: str, context: dict) -> DiagnosisAssessment | None:
        # Interfaz preparada para clasificación semántica mediante LLM en el futuro.
        return None

class DiagnosticEngine:
    def __init__(self, semantic_classifier: SemanticDiagnosisClassifier | None = None) -> None:
        self.semantic_classifier = semantic_classifier or SemanticDiagnosisClassifier()

    async def assess(
        self,
        text: str,
        context: dict[str, Any] | None = None,
        conversation_state: dict[str, Any] | None = None
    ) -> DiagnosisAssessment:
        text_lower = (text or "").lower().strip()
        context = context or {}
        conversation_state = conversation_state or {}

        # 1. Si la fase de la conversación ya es INTAKE, continuar siempre en INTAKE
        current_phase = conversation_state.get("phase")
        if current_phase == "INTAKE":
            return DiagnosisAssessment(state=DiagnosisState.INTAKE)

        # 2. Si el texto contiene términos de seguridad/salud/revisión humana urgente, ir a INTAKE
        # para que el pipeline de admisión normal realice la escalada a revisión humana
        safety_terms = [
            "intoxic", "he respirado", "mareo", "urgencias", "mascota", "perro", "gato",
            "restaurante", "bar", "negocio alimentario", "industria alimentaria",
            "denuncia", "reclamación", "reclamacion", "muy enfadado", "producto químico",
            "producto quimico", "mezclar", "lejía", "lejia", "amoniaco", "garantía total",
            "garantia total", "precio cerrado"
        ]
        if any(term in text_lower for term in safety_terms):
            return DiagnosisAssessment(state=DiagnosisState.INTAKE)

        # 3. Clasificación de Nivel 2: Semántica (opcional)
        semantic_result = await self.semantic_classifier.classify(text_lower, context)
        if semantic_result:
            return semantic_result

        # 4. Nivel 1: Reglas Rápidas (Rule-based)

        # Palabras clave de plagas conocidas directamente para admisión (INTAKE)
        intake_keywords = [
            "cucaracha", "cucarachas", "rata", "ratas", "raton", "ratón", "ratones",
            "roedor", "roedores", "hormiga", "hormigas", "avispa", "avispas",
            "gorgojo", "gorgojos", "polilla", "polillas", "termitas", "termita",
            "chinche", "chinches", "desinsectación", "fumigar", "desratización",
            "bichos verdes", "bichitos verdes", "insectos verdes" # Pero bicho verde activa plant_pests si tiene limonero
        ]

        # Palabras clave de plantas/jardín para diagnóstico (DIAGNOSIS -> plant_pests)
        plant_keywords = [
            "limonero", "naranjo", "árbol", "arbol", "planta", "plantas", "hojas",
            "brotes", "jardín", "jardin", "huerto", "maceta", "rosal", "tomatera",
            "bicho verde", "bichito verde", "insecto verde", "melaza", "cochinilla", 
            "pulgón", "pulgon", "chinche verde", "deformando los brotes", 
            "puntitos moviéndose", "puntitos moviendose"
        ]

        # Palabras clave de negocio / comerciales (están dentro del dominio)
        business_keywords = [
            "precio", "servicio", "presupuesto", "coste", "costo", "tarifa", 
            "contratar", "llamar", "contacto", "información", "informacion",
            "cucarachas", "ratas", "hormigas", "avispas"
        ]

        # Palabras clave del dominio de plagas general
        domain_keywords = intake_keywords + plant_keywords + business_keywords + [
            "bicho", "bichos", "insecto", "insectos", "plaga", "plagas", "nido",
            "fumigación", "fumigacion", "fumigar", "bichito", "bichitos", "bichitos negros",
            "bichos raros", "picadura", "picaduras", "mordedura", "excrementos", "caca"
        ]

        # Comprobar si el texto contiene alguna plaga conocida o términos comerciales e ir a INTAKE
        if any(kw in text_lower for kw in intake_keywords + business_keywords):
            # Pero si contiene "bichos verdes" y "limonero" a la vez, va a diagnóstico
            if "limonero" in text_lower or "planta" in text_lower:
                pass
            else:
                return DiagnosisAssessment(state=DiagnosisState.INTAKE)

        # Comprobar si contiene palabras de plantas e ir a DIAGNOSIS -> plant_pests
        is_plant_related = any(kw in text_lower for kw in plant_keywords)
        
        # O si ya estábamos en diagnosis y el mensaje aporta detalles de follow-up
        prev_diagnosis = conversation_state.get("diagnosis", {}) if current_phase == "DIAGNOSIS" else {}
        is_followup_details = (
            current_phase == "DIAGNOSIS" and
            prev_diagnosis.get("knowledge_key") == "plant_pests" and
            any(word in text_lower for word in ["sí", "si", "no", "hojas", "brotes", "pegajosas", "brillantes", "agrupados"])
        )

        if is_plant_related or is_followup_details:
            evidence = prev_diagnosis.get("evidence", [])
            for kw in plant_keywords + ["sí", "si", "pegajosas", "brillantes", "agrupados"]:
                if kw in text_lower and kw not in evidence:
                    evidence.append(kw)

            confidence = 0.5
            if any(term in text_lower for term in ["sí", "si", "pegajosas", "agrupados", "brotes tiernos"]):
                confidence = 0.85

            state_val = DiagnosisState.DIAGNOSIS
            if confidence >= 0.85 and current_phase == "DIAGNOSIS":
                state_val = DiagnosisState.INTAKE

            hypothesis = DiagnosisHypothesis(
                pest_type="plant_pests",
                label="pulgón verde",
                confidence=confidence,
                evidence=evidence,
                questions=[
                    "¿Los ves agrupados en brotes tiernos o debajo de las hojas?",
                    "¿Notas hojas pegajosas o brillantes?"
                ]
            )

            return DiagnosisAssessment(
                state=state_val,
                hypotheses=[hypothesis],
                reason="Detección de plaga en planta o limonero por palabras clave.",
                knowledge_key="plant_pests"
            )

        # Si el texto está completamente fuera del dominio de plagas, es OUT_OF_DOMAIN
        # Omitir comprobación fuera de dominio si es un saludo corto o pregunta general
        is_greeting_or_short = len(text_lower.split()) <= 2 and any(kw in text_lower for kw in ["hola", "buenas", "tardes", "dias", "días", "hey", "ayuda"])
        
        out_of_domain_phrases = ["me lavo los pies", "lavo los pies", "pies sucios", "lavar los pies"]
        
        is_out_of_domain = any(phrase in text_lower for phrase in out_of_domain_phrases)
        if not is_out_of_domain and not is_greeting_or_short:
            if not any(kw in text_lower for kw in domain_keywords):
                is_out_of_domain = True

        if is_out_of_domain:
            return DiagnosisAssessment(
                state=DiagnosisState.OUT_OF_DOMAIN,
                reason="Mensaje no relacionado con el dominio de plagas."
            )

        return DiagnosisAssessment(state=DiagnosisState.INTAKE)
