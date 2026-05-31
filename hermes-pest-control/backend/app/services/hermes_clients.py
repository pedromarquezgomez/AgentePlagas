from typing import Any

import httpx
from pydantic import ValidationError

from app.config.settings import Settings
from app.schemas.agent_response import AgentResponse
from app.schemas.incoming_message import IncomingMessage


class HermesClientError(RuntimeError):
    pass


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
        text = (incoming_message.text or "").casefold()
        conversation_id = (business_context or {}).get("conversation_id")

        if self._requires_human_review(text):
            return self._build_human_review_response(text)

        pest_type = self._extract_pest_type(text)
        affected_area = self._extract_affected_area(text)
        location = self._extract_location(text)

        missing_fields: list[str] = []
        if not pest_type:
            missing_fields.append("pest_type")
        if not affected_area:
            missing_fields.append("affected_area")
        if not location:
            missing_fields.append("location")

        if not missing_fields:
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
                    "pest_type": pest_type,
                    "location": location,
                    "affected_area": affected_area,
                    "priority": self._priority_for(pest_type),
                    "summary": (
                        f"Cliente informa de presencia de {pest_type} en "
                        f"{affected_area} en {location}."
                    ),
                },
            )

        return AgentResponse(
            reply=self._build_missing_data_reply(missing_fields),
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
        return any(term in text for term in review_terms)

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
            raise HermesClientError("HERMES_API_URL is not configured.")

        payload = {
            "message": incoming_message.model_dump(mode="json"),
            "conversation_history": conversation_history or [],
            "business_context": business_context or default_business_context(),
            "response_contract": "AgentResponse",
        }
        headers = {"Content-Type": "application/json"}
        if self.settings.hermes_api_key:
            headers["Authorization"] = f"Bearer {self.settings.hermes_api_key}"

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
            raise HermesClientError("Hermes Agent request timed out.") from exc
        except httpx.HTTPError as exc:
            raise HermesClientError("Hermes Agent request failed.") from exc

        if response.status_code >= 400:
            raise HermesClientError(
                f"Hermes Agent returned HTTP {response.status_code}."
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise HermesClientError("Hermes Agent returned invalid JSON.") from exc

        try:
            return AgentResponse.model_validate(data)
        except ValidationError as exc:
            raise HermesClientError("Hermes Agent response contract is invalid.") from exc


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
