from typing import Any

import httpx
from pydantic import ValidationError

from app.config.settings import Settings
from app.schemas.agent_response import AgentResponse
from app.schemas.incoming_message import IncomingMessage


class HermesClientError(RuntimeError):
    pass


class HermesMockClient:
    async def process_message(
        self,
        incoming_message: IncomingMessage,
        conversation_history: list[dict[str, Any]] | None = None,
        business_context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        text = (incoming_message.text or "").casefold()
        conversation_id = (business_context or {}).get("conversation_id")

        has_cockroach = "cucaracha" in text or "cucarachas" in text
        has_kitchen = "cocina" in text
        has_torremolinos = "torremolinos" in text

        missing_fields: list[str] = []
        if not has_cockroach:
            missing_fields.append("pest_type")
        if not has_kitchen:
            missing_fields.append("affected_area")
        if not has_torremolinos:
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
                    "pest_type": "cucarachas",
                    "location": "Torremolinos",
                    "affected_area": "cocina",
                    "priority": "high",
                    "summary": (
                        "Cliente informa de presencia de cucarachas en la cocina "
                        "en Torremolinos."
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
