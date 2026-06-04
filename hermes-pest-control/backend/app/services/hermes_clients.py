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

        incident_summary = (business_context or {}).get("incident_summary") or ""
        if "[estado: descartado/cancelado]" in incident_summary.lower():
            return AgentResponse(
                reply="Hola, tu incidencia para el control de plagas ha sido revisada por nuestro equipo y ha sido descartada. Si tienes alguna otra consulta o necesitas asistencia con otro tipo de plaga, no dudes en escribirnos.",
                action={"type": "collect_missing_data", "missing_fields": []},
            )

        incident_id = (business_context or {}).get("incident_id")
        if incident_id:
            if any(k in text for k in ["opción", "opcion", "primera", "segunda", "tercera", "horario"]):
                # Simular la aceptación de una visita
                # En un entorno real, la lógica actualizaría el estado o registraría el evento
                return AgentResponse(
                    reply="Perfecto, he tomado nota de tu preferencia. Confirmaremos tu cita en la mayor brevedad posible tras la revisión de nuestro equipo y operador.",
                    action={"type": "escalate_to_human", "missing_fields": []},
                )
            elif any(k in text for k in ["cómo va", "como va", "estado", "novedades"]):
                return AgentResponse(
                    reply="Tu incidencia se encuentra registrada y en espera de revisión por parte de nuestro equipo.",
                    action={"type": "collect_missing_data", "missing_fields": []},
                )

        if self._requires_human_review(text):
            return self._build_human_review_response(text)

        from app.incidents.intake_service import IncidentIntakeService
        intake_service = IncidentIntakeService()
        state = await intake_service.process_intake(
            incoming_message=incoming_message,
            conversation_history=conversation_history,
            conversation_id=conversation_id,
        )

        if state.requires_human_review:
            return self._build_human_review_response(incoming_message.text or "")


        missing_fields = state.missing_fields

        if not missing_fields:
            if state.customer_name:
                return AgentResponse(
                    reply=f"Gracias, {state.customer_name}. He registrado tu incidencia por presencia de {state.pest_type} en {state.location}.",
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
                return AgentResponse(
                    reply=(
                        "Gracias por la información. He registrado el aviso para que el "
                        "equipo lo revise. Si puedes, envíanos una foto de la zona afectada "
                        "para ayudar al técnico a valorar mejor el caso."
                    ),
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

        if is_legacy_flow:
            reply = self._build_missing_data_reply(missing_fields)
        elif "location" in missing_fields and "customer_name" in missing_fields:
            reply = "Entiendo.  Para registrar la incidencia necesito:\n  - ubicación\n  - nombre de contacto\n  ¿Podrías indicármelos?"
        elif "customer_name" in missing_fields:
            reply = "Necesito también un nombre de contacto para registrar la incidencia."
        else:
            if "location" in missing_fields:
                reply = "Para registrar la incidencia necesito saber la ubicación de la plaga."
            elif "pest_type" in missing_fields:
                reply = "Para registrar la incidencia necesito saber qué tipo de plaga has visto."
            else:
                reply = self._build_missing_data_reply(missing_fields)

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
