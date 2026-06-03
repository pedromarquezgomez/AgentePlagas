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

    area_terms = ["cocina", "garaje", "baño", "bano", "jardín", "jardin", "almacén", "almacen"]

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

    def _extract_customer_name(self, text: str) -> str | None:
        cleaned_text = text.replace(".", "").replace(",", "").strip()
        name_match = re.search(
            r"(?:mi nombre es|soy|me llamo|nombre es)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ]+)",
            cleaned_text,
            re.IGNORECASE
        )
        if name_match:
            return name_match.group(1).strip()
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
            if (role in ("assistant", "outbound", "bot") or msg.get("direction") == "outbound") and "registrad" in text:
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

            c_name = self._extract_customer_name(ut)
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

        ready_for_incident = not missing_fields

        # Motores de priorización y cliente del Sprint 12
        from app.customers.classifier import CustomerTypeClassifier
        from app.incidents.prioritization.engine import IncidentPrioritizationEngine
        from app.pests.contracts import PestClassification

        customer_classifier = CustomerTypeClassifier()
        prioritization_engine = IncidentPrioritizationEngine()

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

        severity = assessment.incident_severity.value
        priority = assessment.incident_priority.value
        requires_human_review = requires_human_review or assessment.requires_human_review
        response_hours = assessment.recommended_response_hours
        assessment_reason = assessment.reason

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
        )
