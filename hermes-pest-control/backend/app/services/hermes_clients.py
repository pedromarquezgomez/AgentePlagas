import logging
from typing import Any

import httpx
from pydantic import ValidationError

from app.config.settings import Settings
from app.schemas.agent_response import AgentResponse
from app.schemas.incoming_message import IncomingMessage

logger = logging.getLogger(__name__)


class HermesClientError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        error_type: str,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.status_code = status_code

    @property
    def normalized_error(self) -> str:
        if self.error_type.startswith("http_"):
            return f"HermesClientError:{self.error_type}"
        if self.status_code is not None:
            return f"HermesClientError:{self.error_type}_{self.status_code}"
        return f"HermesClientError:{self.error_type}"


class HermesMockClient:
    async def process_message(
        self,
        incoming_message: IncomingMessage,
        conversation_history: list[dict[str, Any]] | None = None,
        business_context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        text = (incoming_message.text or "").casefold()
        conversation_id = (business_context or {}).get("conversation_id")

        if self._requires_human_review(text):
            return self._build_human_review_response(text)

        from app.incidents.intake_service import IncidentIntakeService
        intake_service = IncidentIntakeService()
        state = await intake_service.process_intake(
            incoming_message=incoming_message,
            conversation_history=conversation_history,
            conversation_id=conversation_id,
        )

        injected_pest = (business_context or {}).get("injected_pest")
        if injected_pest:
            state.pest_type = "plant_pests"
            state.pest_type_spanish = injected_pest
            if "pest_type" in state.missing_fields:
                state.missing_fields.remove("pest_type")

        if state.requires_human_review:
            return self._build_human_review_response(incoming_message.text or "")

        customer_ctx_dict = (business_context or {}).get("customer_context")
        from app.context.customer_context_builder import CustomerContext
        from app.conversation.missing_data_service import MissingDataService

        customer_context = CustomerContext(**customer_ctx_dict) if customer_ctx_dict else CustomerContext()
        missing_fields = MissingDataService.resolve_missing_fields(state.missing_fields, customer_context)

        # Si tiene múltiples locales, verificar si la ubicación provista coincide con alguno
        if customer_context.has_multiple_sites and customer_context.site_locations:
            matched = False
            loc_val = (state.location or "").lower()
            text_val = (incoming_message.text or "").lower()
            for sl in customer_context.site_locations:
                if sl in loc_val or sl in text_val:
                    matched = True
                    # Normalizar ubicación a la que coincide
                    from app.incidents.intake_service import IncidentIntakeService
                    intake_service = IncidentIntakeService()
                    loc_spanish = sl.capitalize()
                    for k, v in intake_service.normalized_locations.items():
                        if k.casefold() == sl.casefold():
                            loc_spanish = v
                            break
                    state.location = loc_spanish
                    break
            if not matched:
                if "location" not in missing_fields:
                    missing_fields.append("location")
                state.location = None

        # Si hay campos principales faltantes, no pedir el affected_area todavía
        if "location" in missing_fields or "pest_type" in missing_fields or "customer_name" in missing_fields:
            if "affected_area" in missing_fields:
                missing_fields.remove("affected_area")

        # Enriquecer state con datos conocidos para respuestas y creación
        if "customer_name" not in missing_fields and customer_context.customer_name and not state.customer_name:
            state.customer_name = customer_context.customer_name
        if "location" not in missing_fields and customer_context.last_location and not state.location:
            state.location = customer_context.last_location

        intent = (business_context or {}).get("intent")
        is_recurrence = intent == "RECURRENCE"

        from app.config.agent_loader import AgentConfigLoader
        loader = AgentConfigLoader()
        templates = loader.load_response_templates()

        def get_template(section: str, key: str, fallback: str) -> str:
            val = templates.get(section, {}).get(key, {}).get("es")
            return val if val is not None else fallback

        if not missing_fields:
            if is_recurrence:
                pest_name = state.pest_type_spanish or state.pest_type or "plaga"
                loc = state.location or "tu ubicación conocida"
                reply = get_template(
                    "intake",
                    "recurrence_success",
                    "He detectado que esto es una reincidencia de tu caso anterior (ID: {last_incident_id}). Gracias, {customer_name}. He registrado tu incidencia por presencia de {pest_type} en {location}."
                ).format(
                    last_incident_id=customer_context.last_incident_id,
                    customer_name=state.customer_name,
                    pest_type=pest_name,
                    location=loc
                )
                return AgentResponse(
                    reply=reply,
                    action={
                        "type": "create_incident",
                        "missing_fields": [],
                    },
                    incident={
                        "should_create": True,
                        "pest_type": state.pest_type or "COCKROACH",
                        "location": state.location,
                        "affected_area": state.affected_area or "cocina",
                        "priority": _map_priority(state.priority) or state.recommended_priority or self._priority_for(state.pest_type_spanish or state.pest_type),
                        "summary": f"Reincidencia registrada: presencia de {state.pest_type} en {state.location}.",
                        "confidence": state.confidence,
                        "evidence": state.evidence,
                        "detected_terms": state.detected_terms,
                        "severity": state.severity,
                        "response_hours": state.response_hours,
                        "assessment_reason": state.assessment_reason,
                        "visit_type": state.visit_type,
                        "technician_level": state.technician_level,
                        "dispatch_bucket": state.dispatch_bucket,
                        "sla_hours": state.sla_hours,
                    },
                    metadata={
                        "customer_name": state.customer_name,
                        "is_recurrence": True,
                        "parent_incident_id": customer_context.last_incident_id,
                    }
                )

            if state.customer_name:
                if state.pest_type == "plant_pests":
                    reply = get_template(
                        "diagnosis",
                        "confirmed_plant_pest",
                        "El caso es compatible con presencia de pulgón verde. He registrado el aviso para el tratamiento de esta plaga."
                    )
                else:
                    reply = get_template(
                        "intake",
                        "create_success",
                        "Gracias, {customer_name}. He registrado tu incidencia por presencia de {pest_type} en {location}."
                    ).format(
                        customer_name=state.customer_name,
                        pest_type=state.pest_type_spanish or state.pest_type,
                        location=state.location
                    )
                return AgentResponse(
                    reply=reply,
                    action={
                        "type": "create_incident",
                        "missing_fields": [],
                    },
                    incident={
                        "should_create": True,
                        "pest_type": state.pest_type,
                        "location": state.location,
                        "affected_area": state.affected_area or "cocina",
                        "priority": _map_priority(state.priority) or state.recommended_priority or self._priority_for(state.pest_type_spanish or state.pest_type),
                        "summary": f"Cliente informa de presencia de {state.pest_type} en {state.location}.",
                        "confidence": state.confidence,
                        "evidence": state.evidence,
                        "detected_terms": state.detected_terms,
                        "severity": state.severity,
                        "response_hours": state.response_hours,
                        "assessment_reason": state.assessment_reason,
                        "visit_type": state.visit_type,
                        "technician_level": state.technician_level,
                        "dispatch_bucket": state.dispatch_bucket,
                        "sla_hours": state.sla_hours,
                    },
                    metadata={
                        "customer_name": state.customer_name,
                    }
                )
            else:
                reply = get_template(
                    "intake",
                    "create_success_no_name",
                    "Gracias por la información. He registrado el aviso para que el equipo lo revise. Si puedes, envíanos una foto de la zona afectada para ayudar al técnico a valorar mejor el caso."
                )
                return AgentResponse(
                    reply=reply,
                    action={
                        "type": "create_incident",
                        "missing_fields": [],
                    },
                    incident={
                        "should_create": True,
                        "pest_type": state.pest_type_spanish,
                        "location": state.location,
                        "affected_area": state.affected_area,
                        "priority": _map_priority(state.priority) or state.recommended_priority or self._priority_for(state.pest_type_spanish),
                        "summary": (
                            f"Cliente informa de presencia de {state.pest_type_spanish} en "
                            f"{state.affected_area} en {state.location}."
                        ),
                        "confidence": state.confidence,
                        "evidence": state.evidence,
                        "detected_terms": state.detected_terms,
                        "severity": state.severity,
                        "response_hours": state.response_hours,
                        "assessment_reason": state.assessment_reason,
                        "visit_type": state.visit_type,
                        "technician_level": state.technician_level,
                        "dispatch_bucket": state.dispatch_bucket,
                        "sla_hours": state.sla_hours,
                    },
                )

        is_legacy_flow = state.is_legacy_flow
        if customer_context.customer_name:
            is_legacy_flow = False

        if is_legacy_flow:
            reply = self._build_missing_data_reply(missing_fields)
        elif "location" in missing_fields and "customer_name" in missing_fields:
            reply = get_template(
                "intake",
                "missing_location_and_name",
                "Para registrar el aviso necesito la ubicación y un nombre de contacto."
            )
        elif "customer_name" in missing_fields:
            reply = get_template(
                "intake",
                "missing_customer_name",
                "¿A nombre de quién registramos el aviso?"
            )
        elif "affected_area" in missing_fields and state.location and not ("location" in missing_fields or "pest_type" in missing_fields):
            reply = get_template(
                "intake",
                "ask_affected_area",
                "Perfecto, he localizado el aviso en el local de {location}. ¿La actividad está en cocina, almacén, comedor u otra zona?"
            ).format(location=state.location)
        else:
            if "location" in missing_fields:
                reply = get_template(
                    "intake",
                    "missing_location",
                    "Para registrar el aviso necesito saber dónde ocurre. Puede ser localidad, dirección o local afectado."
                )
            elif "pest_type" in missing_fields:
                reply = get_template(
                    "intake",
                    "missing_pest_type",
                    "Para registrar la incidencia necesito saber qué tipo de plaga has visto."
                )
            else:
                reply = self._build_missing_data_reply(missing_fields)

        metadata = {}
        if is_recurrence:
            metadata["is_recurrence"] = True
            metadata["parent_incident_id"] = customer_context.last_incident_id
            if customer_context.customer_name:
                metadata["customer_name"] = customer_context.customer_name
        elif customer_context.customer_name:
            metadata["customer_name"] = customer_context.customer_name

        return AgentResponse(
            reply=reply,
            action={
                "type": "collect_missing_data",
                "missing_fields": missing_fields,
            },
            incident={
                "should_create": False,
                "conversation_id": conversation_id,
            },
            metadata=metadata,
        )

    def _requires_human_review(self, text: str) -> bool:
        cleaned_text = text.replace("bar pepe", "").replace("mi bar", "")
        review_terms = [
            "intoxic",
            "he respirado",
            "mareo",
            "urgencias",
            "mascota",
            "perro",
            "gato",
            "restaurante",
            "bar",
            "negocio alimentario",
            "industria alimentaria",
            "denuncia",
            "reclamación",
            "reclamacion",
            "muy enfadado",
            "producto químico",
            "producto quimico",
            "mezclar",
            "lejía",
            "lejia",
            "amoniaco",
            "garantía total",
            "garantia total",
            "precio cerrado",
        ]
        return any(term in cleaned_text for term in review_terms)

    def _build_human_review_response(self, text: str) -> AgentResponse:
        from app.pests.classifier import PestClassifier
        from app.incidents.intake_service import IncidentIntakeService
        from app.customers.classifier import CustomerTypeClassifier
        from app.incidents.prioritization.engine import IncidentPrioritizationEngine

        classifier = PestClassifier()
        service = IncidentIntakeService(classifier=classifier)
        classified = classifier.classify(text)
        pest_type = classified.pest_type_spanish
        affected_area = service._extract_affected_area(text)
        location = service._extract_location_legacy(text)

        customer_classifier = CustomerTypeClassifier()
        prioritization_engine = IncidentPrioritizationEngine()
        customer_type = customer_classifier.classify(text)

        assessment = prioritization_engine.assess(
            pest_classification=classified,
            location_text=location,
            customer_type=customer_type,
            affected_area=affected_area,
        )

        priority_val = _map_priority(assessment.incident_priority.value)
        if not priority_val or priority_val in {"medium", "low"}:
            priority_val = "high"

        priority = "urgent" if self._is_urgent_review(text) else priority_val


        return AgentResponse(
            reply=(
                "Gracias por avisarnos. Por seguridad, he dejado el caso para que "
                "el equipo lo revise directamente antes de darte instrucciones o "
                "condiciones concretas."
            ),
            action={
                "type": "escalate_to_human",
                "missing_fields": [],
            },
            incident={
                "should_create": True,
                "pest_type": pest_type,
                "location": location,
                "affected_area": affected_area,
                "priority": priority,
                "summary": "Caso sensible o de seguridad que requiere revisión humana.",
                "confidence": classified.confidence,
                "evidence": classified.evidence,
                "detected_terms": classified.detected_terms,
                "severity": assessment.incident_severity.value,
                "response_hours": assessment.recommended_response_hours,
                "assessment_reason": assessment.reason,
            },
        )

    def _is_urgent_review(self, text: str) -> bool:
        return any(
            term in text
            for term in [
                "intoxic",
                "he respirado",
                "mareo",
                "urgencias",
                "mascota",
                "perro",
                "gato",
                "negocio alimentario",
                "restaurante",
                "bar",
                "negocio",
            ]
        )

    def _priority_for(self, pest_type: str | None) -> str:
        if not pest_type:
            return "medium"
        pt_lower = pest_type.lower()
        if pt_lower in {"cucarachas", "roedores", "cockroach", "rodent"}:
            return "high"
        return "medium"

    def _build_missing_data_reply(self, missing_fields: list[str]) -> str:
        prompts = {
            "pest_type": "qué tipo de plaga has visto",
            "affected_area": "en qué zona del inmueble está ocurriendo",
            "location": "en qué localidad se encuentra el aviso",
        }
        requested = [prompts[field] for field in missing_fields]

        if len(requested) == 1:
            details = requested[0]
        else:
            details = ", ".join(requested[:-1]) + f" y {requested[-1]}"

        return f"Para registrar el aviso necesito saber {details}."



class HermesRealClient:
    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.transport = transport

    async def process_message(
        self,
        incoming_message: IncomingMessage,
        conversation_history: list[dict[str, Any]] | None = None,
        business_context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        if not self.settings.hermes_api_url:
            raise HermesClientError(
                "HERMES_API_URL is not configured.",
                error_type="not_configured",
            )

        business_context = business_context or default_business_context()
        trace_id = business_context.get("trace_id")
        available_skills = business_context.pop("available_skills", [])
        available_tools = business_context.pop("available_tools", [])

        payload = {
            "message": incoming_message.model_dump(mode="json"),
            "conversation_history": conversation_history or [],
            "business_context": business_context,
            "available_skills": available_skills,
            "available_tools": available_tools,
            "response_contract": "AgentResponse",
        }
        headers = {"Content-Type": "application/json"}
        if self.settings.hermes_api_key:
            headers["Authorization"] = f"Bearer {self.settings.hermes_api_key.strip()}"
        if self.settings.hermes_shadow_api_key:
            headers["X-Hermes-Agent-Key"] = self.settings.hermes_shadow_api_key.strip()
        if trace_id:
            headers["X-Hermes-Trace-Id"] = str(trace_id)

        try:
            async with httpx.AsyncClient(
                timeout=self.settings.hermes_timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    self.settings.hermes_api_url,
                    json=payload,
                    headers=headers,
                )
        except httpx.TimeoutException as exc:
            self._log_failure(
                trace_id=trace_id,
                error_type="timeout",
                error_class=exc.__class__.__name__,
            )
            raise HermesClientError(
                "Hermes Agent request timed out.",
                error_type="timeout",
            ) from exc
        except httpx.ConnectError as exc:
            self._log_failure(
                trace_id=trace_id,
                error_type="connection_error",
                error_class=exc.__class__.__name__,
            )
            raise HermesClientError(
                "Hermes Agent connection failed.",
                error_type="connection_error",
            ) from exc
        except httpx.HTTPError as exc:
            self._log_failure(
                trace_id=trace_id,
                error_type="request_failed",
                error_class=exc.__class__.__name__,
            )
            raise HermesClientError(
                "Hermes Agent request failed.",
                error_type="request_failed",
            ) from exc

        if response.status_code >= 400:
            error_type = f"http_{response.status_code}"
            self._log_failure(
                trace_id=trace_id,
                error_type=error_type,
                error_class="HTTPStatusError",
                status_code=response.status_code,
            )
            raise HermesClientError(
                f"Hermes Agent returned HTTP {response.status_code}.",
                error_type=error_type,
                status_code=response.status_code,
            )

        try:
            data = response.json()
        except ValueError as exc:
            self._log_failure(
                trace_id=trace_id,
                error_type="invalid_json",
                error_class=exc.__class__.__name__,
                status_code=response.status_code,
            )
            raise HermesClientError(
                "Hermes Agent returned invalid JSON.",
                error_type="invalid_json",
            ) from exc

        try:
            return AgentResponse.model_validate(data)
        except ValidationError as exc:
            self._log_failure(
                trace_id=trace_id,
                error_type="invalid_contract",
                error_class=exc.__class__.__name__,
                status_code=response.status_code,
            )
            raise HermesClientError(
                "Hermes Agent response contract is invalid.",
                error_type="invalid_contract",
            ) from exc

    def _log_failure(
        self,
        *,
        trace_id: Any,
        error_type: str,
        error_class: str,
        status_code: int | None = None,
    ) -> None:
        logger.warning(
            "hermes_real_client_error trace_id=%s hermes_mode=real "
            "error_type=%s error_class=%s status_code=%s",
            trace_id,
            error_type,
            error_class,
            status_code,
        )


def default_business_context(conversation_id: str | None = None) -> dict[str, Any]:
    context = {
        "domain": "pest_control",
        "company_type": "real_company",
        "language": "es",
        "agent_role": "operational_orchestrator",
    }
    if conversation_id:
        context["conversation_id"] = conversation_id
    return context


def _map_priority(priority: str | None) -> str | None:
    if not priority:
        return None
    p_upper = priority.upper()
    if p_upper == "URGENT":
        return "urgent"
    if p_upper == "HIGH":
        return "high"
    if p_upper == "NORMAL":
        return "medium"
    if p_upper == "LOW":
        return "low"
    return "medium"
