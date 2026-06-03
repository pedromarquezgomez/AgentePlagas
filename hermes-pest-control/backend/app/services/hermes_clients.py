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
    pest_terms = {
        "cucaracha": "cucarachas",
        "cucarachas": "cucarachas",
        "hormiga": "hormigas",
        "hormigas": "hormigas",
        "roedor": "roedores",
        "roedores": "roedores",
        "rata": "roedores",
        "ratas": "roedores",
        "ratón": "roedores",
        "ratones": "roedores",
        "raton": "roedores",
        "ratones": "roedores",
    }
    area_terms = ["cocina", "garaje", "baño", "bano", "jardín", "jardin", "almacén", "almacen"]
    location_terms = ["torremolinos", "málaga", "malaga", "benalmádena", "benalmadena", "fuengirola", "marbella"]

    async def process_message(
        self,
        incoming_message: IncomingMessage,
        conversation_history: list[dict[str, Any]] | None = None,
        business_context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        import re
        text = (incoming_message.text or "").casefold()
        conversation_id = (business_context or {}).get("conversation_id")

        if self._requires_human_review(text):
            return self._build_human_review_response(text)

        # Recopilamos todos los mensajes del usuario en el historial + mensaje actual
        user_texts = []
        if conversation_history:
            for msg in conversation_history:
                if isinstance(msg, dict) and msg.get("role") == "user":
                    content = msg.get("content") or msg.get("text")
                    if content:
                        user_texts.append(content)
        if incoming_message.text:
            user_texts.append(incoming_message.text)

        pest_type = None
        pest_type_spanish = None
        location = None
        customer_name = None
        affected_area = None

        for ut in user_texts:
            ut_lower = ut.casefold()
            
            # Clasificación de plaga
            if "cucaracha" in ut_lower:
                pest_type = "cockroach"
                pest_type_spanish = "cucarachas"
            elif any(term in ut_lower for term in ["roedor", "rata", "raton", "ratón", "roedores"]):
                pest_type = "rodent"
                pest_type_spanish = "roedores"
            elif "hormiga" in ut_lower:
                pest_type = "ant"
                pest_type_spanish = "hormigas"

            compat_pest = self._extract_pest_type(ut_lower)
            if compat_pest:
                pest_type_spanish = compat_pest
                if compat_pest == "cucarachas":
                    pest_type = "cockroach"
                elif compat_pest == "roedores":
                    pest_type = "rodent"
                elif compat_pest == "hormigas":
                    pest_type = "ant"

            compat_area = self._extract_affected_area(ut_lower)
            if compat_area:
                affected_area = compat_area

            # Extracción de ubicación libre y compatibilidad
            if "cocina del bar pepe" in ut_lower:
                location = "cocina del Bar Pepe"
            elif "cocina de mi bar" in ut_lower:
                location = "cocina de mi bar"
            elif "la cocina" in ut_lower:
                location = "la cocina"
            elif "cocina" in ut_lower:
                location = "cocina"

            compat_loc = self._extract_location(ut_lower)
            if compat_loc:
                location = compat_loc

            # Extracción de nombre de cliente
            cleaned_ut = ut.replace(".", "").replace(",", "").strip()
            name_match = re.search(r"(?:mi nombre es|soy|me llamo|nombre es)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ]+)", cleaned_ut, re.IGNORECASE)
            if name_match:
                customer_name = name_match.group(1).strip()

        missing_fields = []
        if not pest_type or pest_type == "unknown":
            missing_fields.append("pest_type")
        if not location:
            missing_fields.append("location")
        if not customer_name:
            missing_fields.append("customer_name")

        has_legacy_loc = any(self._extract_location(ut.casefold()) is not None for ut in user_texts)
        is_legacy_flow = (
            not customer_name
            and pest_type_spanish
            and affected_area
            and has_legacy_loc
        )

        if is_legacy_flow:
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
                    "pest_type": pest_type_spanish,
                    "location": location,
                    "affected_area": affected_area,
                    "priority": self._priority_for(pest_type_spanish),
                    "summary": (
                        f"Cliente informa de presencia de {pest_type_spanish} en "
                        f"{affected_area} en {location}."
                    ),
                },
            )

        if not missing_fields:
            return AgentResponse(
                reply=f"Gracias, {customer_name}. He registrado tu incidencia por presencia de {pest_type} en {location}.",
                action={
                    "type": "create_incident",
                    "missing_fields": [],
                },
                incident={
                    "should_create": True,
                    "pest_type": pest_type,
                    "location": location,
                    "affected_area": affected_area or "cocina",
                    "priority": self._priority_for(pest_type_spanish or pest_type),
                    "summary": f"Cliente informa de presencia de {pest_type} en {location}.",
                },
                metadata={
                    "customer_name": customer_name,
                }
            )

        # Si faltan campos
        if "location" in missing_fields and "customer_name" in missing_fields:
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
        # Excluir 'bar pepe' y 'mi bar' de la coincidencia del término sensible 'bar'
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
        pest_type = self._extract_pest_type(text)
        affected_area = self._extract_affected_area(text)
        location = self._extract_location(text)
        priority = "urgent" if self._is_urgent_review(text) else "high"

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
            ]
        )

    def _extract_pest_type(self, text: str) -> str | None:
        for term, pest_type in self.pest_terms.items():
            if term in text:
                return pest_type
        return None

    def _extract_affected_area(self, text: str) -> str | None:
        for area in self.area_terms:
            if area in text:
                if area == "bano":
                    return "baño"
                if area == "jardin":
                    return "jardín"
                if area == "almacen":
                    return "almacén"
                return area
        return None

    def _extract_location(self, text: str) -> str | None:
        normalized_names = {
            "torremolinos": "Torremolinos",
            "málaga": "Málaga",
            "malaga": "Málaga",
            "benalmádena": "Benalmádena",
            "benalmadena": "Benalmádena",
            "fuengirola": "Fuengirola",
            "marbella": "Marbella",
        }
        for location in self.location_terms:
            if location in text:
                return normalized_names[location]
        return None

    def _priority_for(self, pest_type: str | None) -> str:
        if pest_type in {"cucarachas", "roedores"}:
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
