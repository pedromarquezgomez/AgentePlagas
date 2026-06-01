import logging
from typing import Any

from app.config.settings import Settings
from app.schemas.agent_response import AgentResponse
from app.schemas.incoming_message import IncomingMessage
from app.services.hermes_clients import (
    HermesClientError,
    HermesMockClient,
    HermesRealClient,
    default_business_context,
)

logger = logging.getLogger(__name__)


class HermesService:
    def __init__(
        self,
        settings: Settings | None = None,
        client: HermesMockClient | HermesRealClient | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.hermes_mode = self.settings.hermes_mode.casefold()
        self.client = client or self._build_client()

    async def process_message(
        self,
        incoming_message: IncomingMessage,
        conversation_history: list[dict[str, Any]] | str | None = None,
        business_context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        conversation_history, business_context = self._normalize_context_args(
            conversation_history,
            business_context,
        )
        logger.info(
            "hermes_request_started hermes_mode=%s channel=%s message_type=%s "
            "attachment_count=%s",
            self.hermes_mode,
            incoming_message.channel,
            incoming_message.message_type,
            len(incoming_message.attachments),
        )

        try:
            response = await self.client.process_message(
                incoming_message,
                conversation_history=conversation_history,
                business_context=business_context,
            )
            logger.info(
                "hermes_request_completed hermes_mode=%s action_type=%s",
                self.hermes_mode,
                response.action.type,
            )
            return response
        except HermesClientError as exc:
            logger.warning(
                "hermes_response_invalid hermes_mode=%s error_type=%s "
                "status_code=%s error=%s",
                self.hermes_mode,
                exc.error_type,
                exc.status_code,
                exc,
            )
            return self._safe_fallback_response(exc.normalized_error)
        except Exception as exc:
            logger.warning(
                "hermes_response_invalid hermes_mode=%s error=%s",
                self.hermes_mode,
                exc.__class__.__name__,
            )
            return self._safe_fallback_response(
                f"UnexpectedError:{exc.__class__.__name__}"
            )

    def _build_client(self) -> HermesMockClient | HermesRealClient:
        if self.hermes_mode == "real":
            return HermesRealClient(self.settings)
        return HermesMockClient()

    def _normalize_context_args(
        self,
        conversation_history: list[dict[str, Any]] | str | None,
        business_context: dict[str, Any] | None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if isinstance(conversation_history, str):
            return [], business_context or default_business_context(conversation_history)
        return (
            conversation_history or [],
            business_context or default_business_context(),
        )

    def _safe_fallback_response(self, fallback_reason: str = "hermes_service_error") -> AgentResponse:
        logger.info("hermes_fallback_used hermes_mode=%s", self.hermes_mode)
        return AgentResponse(
            reply=(
                "Ahora mismo no he podido procesar correctamente tu solicitud. "
                "He dejado constancia para que el equipo lo revise."
            ),
            action={
                "type": "escalate_to_human",
                "missing_fields": [],
            },
            incident={
                "should_create": True,
                "pest_type": None,
                "location": None,
                "affected_area": None,
                "priority": "medium",
                "summary": "Error procesando respuesta del agente. Requiere revisión humana.",
            },
            metadata={
                "fallback_used": True,
                "fallback_reason": fallback_reason,
            },
        )
