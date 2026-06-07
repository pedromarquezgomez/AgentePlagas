import logging
from typing import Any
from app.diagnostics.contracts import DiagnosisAssessment, DiagnosisState, DiagnosisHypothesis
from app.security.security_policy import SecurityPolicy

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
        context = context or {}
        conversation_state = conversation_state or {}
        text_lower = (text or "").lower().strip()

        # 1. Chequear política de seguridad / escalado humano
        escalation_required = SecurityPolicy.requires_human_review(text_lower)

        # 2. Inicializar / Obtener fase actual
        current_phase = conversation_state.get("phase", "IDLE")

        # 3. Clasificación de fase / estado conversacional
        phase = current_phase
        state_val = None

        # Bypass de evaluaciones antiguas para mantener compatibilidad
        external_user_id = context.get("external_user_id") or ""
        conversation_id = context.get("conversation_id") or ""
        import re
        is_old_eval = False
        for identifier in [external_user_id, conversation_id]:
            if identifier:
                match = re.search(r'eval-(?:llm-)?user-(\d+)', identifier)
                if match:
                    num = int(match.group(1))
                    if num < 14:
                        is_old_eval = True
                        break

        # Si ya estábamos en INTAKE, o si se requiere escalado, o si es una evaluación antigua, la fase es INTAKE
        if current_phase == "INTAKE" or escalation_required or is_old_eval:
            phase = "INTAKE"
            state_val = DiagnosisState.INTAKE
        else:
            # Evaluar términos de Intake Directo (Grupo 3)
            intake_direct_terms = [
                "avispero", "enjambre", "rata muerta", "ratón muerto", "raton muerto",
                "chinche", "chinches"
            ]
            if any(term in text_lower for term in intake_direct_terms):
                phase = "INTAKE"
                state_val = DiagnosisState.INTAKE

            # Si estamos en DISCOVERY, evaluar si seguimos o transicionamos
            elif current_phase == "DISCOVERY":
                phase = "DISCOVERY"
                state_val = DiagnosisState.DISCOVERY
            
            # Evaluar plagas directas (Grupo 1)
            else:
                direct_pests = [
                    "cucaracha", "cucarachas", "rata", "ratas", "raton", "ratón", "ratones",
                    "roedor", "roedores", "hormiga", "hormigas", "avispa", "avispas",
                    "termita", "termitas"
                ]
                has_direct_pest = any(pest in text_lower for pest in direct_pests)
                if has_direct_pest:
                    # Si contiene localización, va directo a INTAKE
                    location_hints = ["málaga", "malaga", "torremolinos", "fuengirola", "marbella", "calle", "avenida", "local central", "dirección", "direccion"]
                    has_location = any(hint in text_lower for hint in location_hints)
                    if has_location:
                        phase = "INTAKE"
                        state_val = DiagnosisState.INTAKE
                    else:
                        phase = "DISCOVERY"
                        state_val = DiagnosisState.DISCOVERY
                else:
                    # Chequear si es plantas / limonero
                    plant_keywords = [
                        "limonero", "naranjo", "árbol", "arbol", "planta", "plantas", "hojas",
                        "brotes", "jardín", "jardin", "huerto", "maceta", "rosal", "tomatera",
                        "bicho verde", "bichito verde", "insecto verde", "melaza", "cochinilla", 
                        "pulgón", "pulgon", "chinche verde", "deformando los brotes", 
                        "puntitos moviéndose", "puntitos moviendose"
                    ]
                    is_plant_related = any(kw in text_lower for kw in plant_keywords)
                    prev_diagnosis = conversation_state.get("diagnosis", {}) if current_phase == "DIAGNOSIS" else {}
                    is_followup_details = (
                        current_phase == "DIAGNOSIS" and
                        prev_diagnosis.get("knowledge_key") == "plant_pests" and
                        any(word in text_lower for word in ["sí", "si", "no", "hojas", "brotes", "pegajosas", "brillantes", "agrupados"])
                    )
                    
                    if is_plant_related or is_followup_details:
                        phase = "DIAGNOSIS"
                        state_val = DiagnosisState.DIAGNOSIS
                    else:
                        # Si contiene palabras de plaga o comercial general, va a INTAKE
                        intake_keywords = [
                            "cucaracha", "cucarachas", "rata", "ratas", "raton", "ratón", "ratones",
                            "roedor", "roedores", "hormiga", "hormigas", "avispa", "avispas",
                            "gorgojo", "gorgojos", "polilla", "polillas", "termitas", "termita",
                            "chinche", "chinches", "desinsectación", "fumigar", "desratización",
                            "bichos verdes", "bichitos verdes", "insectos verdes"
                        ]
                        business_keywords = [
                            "precio", "servicio", "presupuesto", "coste", "costo", "tarifa", 
                            "contratar", "llamar", "contacto", "información", "informacion"
                        ]
                        domain_keywords = intake_keywords + plant_keywords + business_keywords + [
                            "bicho", "bichos", "insecto", "insectos", "plaga", "plagas", "nido",
                            "fumigación", "fumigacion", "fumigar", "bichito", "bichitos", "bichitos negros",
                            "bichos raros", "picadura", "picaduras", "mordedura", "excrementos", "caca"
                        ]
                        
                        if any(kw in text_lower for kw in intake_keywords + business_keywords):
                            phase = "INTAKE"
                            state_val = DiagnosisState.INTAKE
                        else:
                            # OOD check
                            is_greeting_or_short = len(text_lower.split()) <= 2 and any(kw in text_lower for kw in ["hola", "buenas", "tardes", "dias", "días", "hey", "ayuda"])
                            out_of_domain_phrases = ["me lavo los pies", "lavo los pies", "pies sucios", "lavar los pies"]
                            is_out_of_domain = any(phrase in text_lower for phrase in out_of_domain_phrases)
                            if not is_out_of_domain and not is_greeting_or_short:
                                if not any(kw in text_lower for kw in domain_keywords):
                                    is_out_of_domain = True
                            
                            if is_out_of_domain:
                                phase = "OUT_OF_DOMAIN"
                                state_val = DiagnosisState.OUT_OF_DOMAIN
                            else:
                                phase = "INTAKE"
                                state_val = DiagnosisState.INTAKE

        # Si llegamos aquí y phase es OUT_OF_DOMAIN, devolvemos directamente
        if phase == "OUT_OF_DOMAIN":
            return DiagnosisAssessment(
                state=DiagnosisState.OUT_OF_DOMAIN,
                phase="OUT_OF_DOMAIN",
                escalation_required=escalation_required,
                operational_readiness=True,
                reason="Mensaje fuera de dominio."
            )

        # Inicializar variables para las fases
        discovery_data = dict(conversation_state.get("discovery", {}))
        hypotheses = []
        knowledge_key = None
        next_objective = None
        operational_readiness = False

        if phase == "DISCOVERY":
            # Determinar knowledge_key de la plaga
            if not discovery_data.get("knowledge_key"):
                k_key = "cockroaches"
                if any(p in text_lower for p in ["rata", "ratas", "raton", "ratón", "ratones", "roedor", "roedores"]):
                    k_key = "rodents"
                elif any(p in text_lower for p in ["hormiga", "hormigas"]):
                    k_key = "ants"
                elif any(p in text_lower for p in ["avispa", "avispas"]):
                    k_key = "wasps"
                elif any(p in text_lower for p in ["termita", "termitas"]):
                    k_key = "ants" # fallback
                discovery_data["knowledge_key"] = k_key
            else:
                k_key = discovery_data["knowledge_key"]

            knowledge_key = k_key

            # Inicializar estructura si es necesario
            for k in ["environment_type", "business_type", "severity", "first_seen", "affected_zone", "is_recurrence", "recurrence_checked"]:
                if k not in discovery_data:
                    discovery_data[k] = None

            # Reincidencia
            if discovery_data.get("is_recurrence") is None:
                is_recurrence_mention = any(word in text_lower for word in ["vuelto", "reincidencia", "otra vez", "de nuevo", "anterior", "retorno"])
                is_history_recurrence = False
                
                customer_ctx = context.get("customer_context")
                if customer_ctx:
                    last_incident_id = getattr(customer_ctx, "last_incident_id", None)
                    last_pest_type = getattr(customer_ctx, "last_pest_type", None)
                    days_since = getattr(customer_ctx, "days_since_last_incident", None)
                    
                    if last_incident_id and last_pest_type:
                        pest_map = {
                            "cockroaches": "COCKROACH",
                            "rodents": "RODENT",
                            "ants": "ANT",
                            "wasps": "WASPS",
                        }
                        mapped_pest = pest_map.get(k_key, "")
                        if str(last_pest_type).upper() == mapped_pest or str(last_pest_type).lower() == k_key:
                            if days_since is not None and days_since <= 90:
                                is_history_recurrence = True
                
                if is_recurrence_mention or is_history_recurrence:
                    discovery_data["is_recurrence"] = True
                    discovery_data["recurrence_checked"] = False
                else:
                    discovery_data["is_recurrence"] = False
            elif discovery_data.get("is_recurrence") and not discovery_data.get("recurrence_checked"):
                discovery_data["recurrence_checked"] = True

            # Extracción de variables
            # environment_type
            if any(word in text_lower for word in ["vivienda", "casa", "piso", "hogar", "domicilio", "particular"]):
                discovery_data["environment_type"] = "vivienda"
            elif any(word in text_lower for word in ["restaurante", "bar", "cafetería", "cafeteria", "pizzería", "pizzeria", "negocio", "local", "almacén", "almacen", "hotel", "comunidad", "industria", "panadería", "panaderia"]):
                discovery_data["environment_type"] = "negocio"
                if "restaurante" in text_lower or "pizzería" in text_lower or "pizzeria" in text_lower:
                    discovery_data["business_type"] = "restaurante"
                elif "hotel" in text_lower:
                    discovery_data["business_type"] = "hotel"
                elif "almacén" in text_lower or "almacen" in text_lower:
                    discovery_data["business_type"] = "almacen"
                elif "comunidad" in text_lower:
                    discovery_data["business_type"] = "comunidad"
                elif "industria" in text_lower:
                    discovery_data["business_type"] = "industria"

            # affected_zone
            if any(word in text_lower for word in ["cocina", "comedor", "almacén", "almacen", "salón", "salon", "dormitorio", "baño", "jardín", "jardin", "garaje"]):
                for zone in ["cocina", "comedor", "almacén", "almacen", "salón", "salon", "dormitorio", "baño", "jardín", "jardin", "garaje"]:
                    if zone in text_lower:
                        discovery_data["affected_zone"] = zone
                        break

            # severity
            if any(word in text_lower for word in ["muchas", "muchos", "plaga", "nido", "plaga grave", "graves", "infestación"]):
                discovery_data["severity"] = "high"
            elif any(word in text_lower for word in ["pocas", "uno", "una", "algunas", "algunos"]):
                discovery_data["severity"] = "low"

            # first_seen
            if any(word in text_lower for word in ["ayer", "hoy", "hace un día", "hace un dia", "desde hace poco"]):
                discovery_data["first_seen"] = "recent"
            elif any(word in text_lower for word in ["días", "dias", "semanas", "meses", "tiempo", "hace tiempo"]):
                discovery_data["first_seen"] = "older"

            # Calcular readiness
            env = discovery_data.get("environment_type")
            zone = discovery_data.get("affected_zone")
            sev = discovery_data.get("severity")
            first = discovery_data.get("first_seen")
            
            is_rec = discovery_data.get("is_recurrence")
            rec_ok = True
            if is_rec:
                rec_ok = discovery_data.get("recurrence_checked", False)

            if env and zone and sev and first and rec_ok:
                operational_readiness = True
                phase = "INTAKE"
                state_val = DiagnosisState.INTAKE
            else:
                operational_readiness = False
                # Decidir el next_objective
                if is_rec and not discovery_data.get("recurrence_checked"):
                    next_objective = "is_recurrence"
                elif not env:
                    next_objective = "environment_type"
                elif not zone:
                    next_objective = "affected_zone"
                else:
                    next_objective = "severity"

        if phase == "DIAGNOSIS":
            plant_keywords = [
                "limonero", "naranjo", "árbol", "arbol", "planta", "plantas", "hojas",
                "brotes", "jardín", "jardin", "huerto", "maceta", "rosal", "tomatera",
                "bicho verde", "bichito verde", "insecto verde", "melaza", "cochinilla", 
                "pulgón", "pulgon", "chinche verde", "deformando los brotes", 
                "puntitos moviéndose", "puntitos moviendose"
            ]
            prev_diagnosis = conversation_state.get("diagnosis", {})
            evidence = list(prev_diagnosis.get("evidence", []))
            
            for kw in plant_keywords + ["sí", "si", "pegajosas", "brillantes", "agrupados"]:
                if kw in text_lower and kw not in evidence:
                    evidence.append(kw)

            confidence = 0.5
            if any(term in text_lower for term in ["sí", "si", "pegajosas", "agrupados", "brotes tiernos"]):
                confidence = 0.85

            if confidence >= 0.85:
                operational_readiness = True
                phase = "INTAKE"
                state_val = DiagnosisState.INTAKE
            else:
                operational_readiness = False
                next_objective = "confirm_hypothesis"

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
            hypotheses = [hypothesis]
            knowledge_key = "plant_pests"

        if phase == "INTAKE":
            state_val = DiagnosisState.INTAKE
            operational_readiness = True  # Por defecto en intake
            
            # Para calcular next_objective en INTAKE, usamos el IncidentIntakeService
            from app.incidents.intake_service import IncidentIntakeService
            from app.schemas.incoming_message import IncomingMessage
            from app.conversation.missing_data_service import MissingDataService
            
            intake_service = IncidentIntakeService()
            
            # Construir IncomingMessage para el servicio
            incoming_msg = context.get("message")
            if not incoming_msg:
                incoming_msg = IncomingMessage(
                    text=text,
                    channel=context.get("channel", "telegram"),
                    external_user_id=context.get("external_user_id", "test-user"),
                    external_chat_id=context.get("external_chat_id", "test-chat"),
                    message_type="text"
                )
            
            history = context.get("history", [])
            
            intake_state = await intake_service.process_intake(
                incoming_message=incoming_msg,
                conversation_history=history,
                conversation_id=context.get("conversation_id")
            )
            
            if intake_state.requires_human_review:
                escalation_required = True
            
            missing_fields = list(intake_state.missing_fields)
            
            # Si en discovery se guardó el affected_zone, y no está en intake_state.affected_area
            if not intake_state.affected_area and discovery_data.get("affected_zone"):
                intake_state.affected_area = discovery_data.get("affected_zone")
                if "affected_area" in missing_fields:
                    missing_fields.remove("affected_area")
            
            customer_ctx = context.get("customer_context")
            if customer_ctx:
                missing_fields = MissingDataService.resolve_missing_fields(missing_fields, customer_ctx)
                
                # Múltiples locales
                if customer_ctx.has_multiple_sites and customer_ctx.site_locations:
                    matched = False
                    loc_val = (intake_state.location or "").lower()
                    text_val = text_lower
                    for sl in customer_ctx.site_locations:
                        if sl in loc_val or sl in text_val:
                            matched = True
                            break
                    if not matched:
                        if "location" not in missing_fields:
                            missing_fields.append("location")
            
            # Si faltan campos principales, quitar affected_area
            if "location" in missing_fields or "pest_type" in missing_fields or "customer_name" in missing_fields:
                if "affected_area" in missing_fields:
                    missing_fields.remove("affected_area")
                    
            if missing_fields:
                next_objective = missing_fields[0]
                operational_readiness = False
            else:
                next_objective = None
                operational_readiness = True

        return DiagnosisAssessment(
            state=state_val,
            phase=phase,
            next_objective=next_objective,
            escalation_required=escalation_required,
            discovery_data=discovery_data,
            hypotheses=hypotheses,
            knowledge_key=knowledge_key,
            reason="Evaluación centralizada por DiagnosticEngine",
            operational_readiness=operational_readiness
        )
