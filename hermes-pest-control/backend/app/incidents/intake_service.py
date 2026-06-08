import logging
import re
from typing import Any

from app.schemas.incoming_message import IncomingMessage
from app.incidents.contracts import IncidentIntakeState

logger = logging.getLogger(__name__)


class IncidentIntakeService:
    def __init__(self, classifier: Any = None) -> None:
        from app.pests.classifier import PestClassifier
        self.classifier = classifier or PestClassifier()

    area_terms = ["cocina", "garaje", "baño", "bano", "jardín", "jardin", "almacén", "almacen", "salón", "salon", "comedor"]

    location_terms = ["torremolinos", "málaga", "malaga", "benalmádena", "benalmadena", "fuengirola", "marbella"]

    normalized_locations = {
        "torremolinos": "Torremolinos",
        "málaga": "Málaga",
        "malaga": "Málaga",
        "benalmádena": "Benalmádena",
        "benalmadena": "Benalmádena",
        "fuengirola": "Fuengirola",
        "marbella": "Marbella",
    }

    def _extract_affected_area(self, text: str) -> str | None:
        text_lower = text.casefold()
        for area in self.area_terms:
            if area in text_lower:
                if area == "bano":
                    return "baño"
                if area == "jardin":
                    return "jardín"
                if area == "almacen":
                    return "almacén"
                if area == "salon":
                    return "salón"
                return area
        return None

    def _extract_location_legacy(self, text: str) -> str | None:
        text_lower = text.casefold()
        for loc in self.location_terms:
            if loc in text_lower:
                return self.normalized_locations[loc]
        return None

    def _extract_free_location(self, text: str) -> str | None:
        pattern = r"(?:es en la|es en el|es en|en la|en el|en)\s+([^.,\n]+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            loc = match.group(1).strip()
            stop_words = ["desde", "hace", "mi nombre", "soy", "y ", "con ", "para ", "creo", "quiero"]
            for word in stop_words:
                pattern_stop = r"\b" + re.escape(word)
                stop_match = re.search(pattern_stop, loc, re.IGNORECASE)
                if stop_match:
                    loc = loc[:stop_match.start()].strip()
            if loc:
                start_idx = text.lower().find(loc.lower())
                if start_idx != -1:
                    return text[start_idx:start_idx+len(loc)].strip()
                return loc
        return None

    def _extract_customer_name(self, text: str, bot_asked_for_name: bool = False) -> str | None:
        # 1. Intentar buscar de negocio/roles: "soy el encargado de Pizzería Roma", "soy gerente de Bar Pepe"
        role_pattern = r"(?:encargado|encargada|gerente|propietario|propietaria|dueño|dueña|empleado|empleada|de parte de|representante|responsable|administrador|administradora|director|directora|socio|socia)\s+de\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+)"
        match = re.search(role_pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            name = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()]+$', '', name).strip()
            return name

        # 2. Intentar buscar nombres personales ignorando artículos y roles
        name_match = re.search(
            r"(?:mi nombre es|soy|me llamo|nombre es)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+)",
            text,
            re.IGNORECASE
        )
        if name_match:
            val = name_match.group(1).strip()
            val = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()]+$', '', val).strip()
            words = val.split()
            if words:
                blacklist = {
                    "el", "la", "un", "una", "los", "las", "mi", "tu", "su",
                    "encargado", "encargada", "gerente", "propietario", "propietaria",
                    "dueño", "dueña", "empleado", "empleada", "tecnico", "técnico", "de",
                    "representante", "responsable", "administrador", "administradora",
                    "director", "directora", "socio", "socia"
                }
                first_word = words[0].lower()
                if first_word in blacklist:
                    if len(words) > 1 and words[0].lower() in {"el", "la", "un", "una"}:
                        second_word = words[1]
                        if second_word.lower() not in blacklist:
                            return second_word
                    return None
                return words[0]

        # 3. Si el bot acaba de preguntar por el nombre, interpretar la respuesta
        #    directa como nombre (ej: el usuario escribe solo "pedro" o "Pedro García")
        if bot_asked_for_name:
            clean = text.strip()
            clean = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()!¡?¿]+$', '', clean).strip()
            words = clean.split()
            # Descartar si contiene palabras que son claramente otra cosa
            non_name_words = {
                "hola", "buenas", "ok", "vale", "sí", "si", "no", "gracias",
                "cucaracha", "cucarachas", "rata", "ratas", "hormiga", "hormigas",
                "avispa", "avispas", "termita", "termitas", "plaga", "plagas",
                "cocina", "baño", "salón", "salon", "almacén", "almacen",
                "madrid", "málaga", "malaga", "barcelona", "sevilla",
                "precio", "presupuesto", "servicio", "ayuda"
            }
            if 1 <= len(words) <= 4 and not any(w.lower() in non_name_words for w in words):
                # Capitalizar y devolver como nombre
                return " ".join(w.capitalize() for w in words)

        return None

    async def process_intake(
        self,
        incoming_message: IncomingMessage,
        conversation_history: list[dict[str, Any]] | None = None,
        conversation_id: str | None = None,
    ) -> IncidentIntakeState:
        all_messages = []
        if conversation_history:
            all_messages.extend(conversation_history)

        all_messages.append({
            "role": "user",
            "text": incoming_message.text or "",
            "direction": "inbound"
        })

        cutoff_index = -1
        for i, msg in enumerate(all_messages):
            role = msg.get("role")
            text = (msg.get("content") or msg.get("text") or "").casefold()
            if role in ("assistant", "outbound", "bot") or msg.get("direction") == "outbound":
                is_success = False
                if any(term in text for term in ["he registrado", "he dejado el caso", "voy a pasar este caso", "registrado por el equipo", "incidencia registrada", "aviso registrado", "caso registrado"]):
                    if "para registrar" not in text and "necesito" not in text:
                        is_success = True
                if is_success:
                    cutoff_index = i

        user_texts = []
        for msg in all_messages[cutoff_index + 1:]:
            role = msg.get("role")
            direction = msg.get("direction")
            if role == "user" or direction == "inbound":
                content = msg.get("content") or msg.get("text")
                if content:
                    user_texts.append(content)

        pest_type = None
        pest_type_spanish = None
        confidence = None
        evidence = None
        detected_terms = []
        recommended_priority = None
        requires_human_review = False
        location = None
        customer_name = None
        affected_area = None
        localidad_detectada = None

        # Detectar si el último mensaje del bot preguntaba por el nombre
        bot_asked_for_name = False
        for msg in reversed(all_messages[cutoff_index + 1:]):
            role = msg.get("role")
            direction = msg.get("direction")
            if role in ("assistant", "outbound", "bot") or direction == "outbound":
                bot_text = (msg.get("content") or msg.get("text") or "").lower()
                if any(phrase in bot_text for phrase in [
                    "me indicas tu nombre", "indícame tu nombre", "¿cómo te llamas",
                    "con quién estoy hablando", "tu nombre", "nombre, por favor"
                ]):
                    bot_asked_for_name = True
                break

        for ut in user_texts:
            classified = self.classifier.classify(ut)
            if classified.pest_type:
                pest_type = classified.pest_type
                pest_type_spanish = classified.pest_type_spanish
                confidence = classified.confidence
                evidence = classified.evidence
                detected_terms = classified.detected_terms
                recommended_priority = classified.recommended_priority
                requires_human_review = classified.requires_human_review

            area = self._extract_affected_area(ut)
            if area:
                affected_area = area

            c_name = self._extract_customer_name(ut, bot_asked_for_name=bot_asked_for_name)
            if c_name:
                customer_name = c_name

            loc_leg = self._extract_location_legacy(ut)
            if loc_leg:
                localidad_detectada = loc_leg

            free_loc = self._extract_free_location(ut)
            if free_loc:
                location = free_loc

        if localidad_detectada:
            location = localidad_detectada

        if location and affected_area and location.casefold() == affected_area.casefold():
            if not customer_name and not localidad_detectada:
                location = None

        # Identificar flujo a evaluar
        is_legacy_flow = False
        if not customer_name:
            has_valid_free_location = location and (not affected_area or location.casefold() != affected_area.casefold())
            if localidad_detectada or (affected_area and not has_valid_free_location):
                is_legacy_flow = True

        missing_fields = []
        if is_legacy_flow:
            if not pest_type_spanish:
                missing_fields.append("pest_type")
            if not location:
                missing_fields.append("location")
            if not affected_area:
                missing_fields.append("affected_area")
        else:
            if not pest_type or pest_type == "UNKNOWN":
                missing_fields.append("pest_type")
            if not location:
                missing_fields.append("location")
            if not customer_name:
                missing_fields.append("customer_name")

            # Pedir affected_area si los campos principales están resueltos pero falta el área
            if not affected_area and not ("pest_type" in missing_fields or "location" in missing_fields or "customer_name" in missing_fields):
                missing_fields.append("affected_area")

        ready_for_incident = not missing_fields

        # Motores de priorización y cliente del Sprint 12
        from app.customers.classifier import CustomerTypeClassifier
        from app.incidents.prioritization.engine import IncidentPrioritizationEngine
        from app.pests.contracts import PestClassification
        from app.incidents.dispatch.engine import DispatchAssessmentEngine

        customer_classifier = CustomerTypeClassifier()
        prioritization_engine = IncidentPrioritizationEngine()
        dispatch_engine = DispatchAssessmentEngine()

        all_user_text = " ".join(user_texts)
        customer_type = customer_classifier.classify(all_user_text)

        pest_classification = PestClassification(
            pest_type=pest_type,
            confidence=confidence,
            evidence=evidence,
            detected_terms=detected_terms,
            recommended_priority=recommended_priority,
            requires_human_review=requires_human_review,
            pest_type_spanish=pest_type_spanish,
        )

        assessment = prioritization_engine.assess(
            pest_classification=pest_classification,
            location_text=location,
            customer_type=customer_type,
            affected_area=affected_area,
        )

        severity = assessment.incident_severity
        priority = assessment.incident_priority
        requires_human_review = requires_human_review or assessment.requires_human_review
        response_hours = assessment.recommended_response_hours
        assessment_reason = assessment.reason

        dispatch_assessment = dispatch_engine.assess(
            incident_assessment=assessment,
            pest_classification=pest_classification,
            customer_type=customer_type,
        )

        return IncidentIntakeState(
            pest_type=pest_type,
            pest_type_spanish=pest_type_spanish,
            location=location,
            customer_name=customer_name,
            affected_area=affected_area,
            missing_fields=missing_fields,
            ready_for_incident=ready_for_incident,
            is_legacy_flow=is_legacy_flow,
            confidence=confidence,
            evidence=evidence,
            detected_terms=detected_terms,
            recommended_priority=recommended_priority,
            requires_human_review=requires_human_review,
            severity=severity,
            priority=priority,
            response_hours=response_hours,
            assessment_reason=assessment_reason,
            visit_type=dispatch_assessment.visit_type,
            technician_level=dispatch_assessment.technician_level,
            dispatch_bucket=dispatch_assessment.dispatch_bucket,
            sla_hours=dispatch_assessment.sla_hours,
        )
