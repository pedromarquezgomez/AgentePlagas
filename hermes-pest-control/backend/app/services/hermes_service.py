import logging
from typing import Any

from app.config.settings import Settings
from app.harness.contracts import AgentRuntimeRequest
from app.harness.providers.hermes_http_provider import HermesHttpRuntimeProvider
from app.harness.providers.llm_provider import LLMRuntimeProvider
from app.harness.providers.mock_provider import MockAgentRuntimeProvider
from app.harness.runtime import AgentRuntimeProvider, LegacyClientRuntimeProvider
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
        provider: AgentRuntimeProvider | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.agent_provider = self._resolve_agent_provider()
        self.hermes_mode = self._legacy_hermes_mode_for_provider()
        self.provider = provider or self._build_provider(client)
        self.client = client or getattr(self.provider, "client", self.provider)

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
            "attachment_count=%s agent_provider=%s",
            self.hermes_mode,
            incoming_message.channel,
            incoming_message.message_type,
            len(incoming_message.attachments),
            self.agent_provider,
        )

        try:
            response = await self.provider.process(
                AgentRuntimeRequest(
                    incoming_message=incoming_message,
                    conversation_history=conversation_history,
                    business_context=business_context,
                )
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

    def _build_provider(
        self,
        client: HermesMockClient | HermesRealClient | None = None,
    ) -> AgentRuntimeProvider:
        if client is not None:
            return LegacyClientRuntimeProvider(
                client,
                name=f"{self.hermes_mode}_legacy_client",
                mode=self.hermes_mode,
            )
        if self.agent_provider == "llm":
            return LLMRuntimeProvider(self.settings)
        if self.agent_provider == "nous_hermes":
            return HermesHttpRuntimeProvider(self.settings)
        return MockAgentRuntimeProvider()

    def _resolve_agent_provider(self) -> str:
        configured_provider = self.settings.agent_provider.strip().casefold()
        if configured_provider:
            return configured_provider

        legacy_mode = self.settings.hermes_mode.casefold()
        if legacy_mode == "real":
            return "nous_hermes"
        return "mock"

    def _legacy_hermes_mode_for_provider(self) -> str:
        if not self.settings.agent_provider.strip():
            return self.settings.hermes_mode.casefold()
        if self.agent_provider == "mock":
            return "mock"
        return self.agent_provider

    @classmethod
    def for_shadow(cls, settings: Settings) -> "HermesService":
        shadow_settings = Settings(
            hermes_mode="real",
            hermes_api_url=settings.hermes_shadow_api_url,
            hermes_shadow_api_key=settings.hermes_shadow_api_key,
            hermes_timeout_seconds=settings.hermes_shadow_timeout_seconds,
        )
        return cls(settings=shadow_settings)

    @classmethod
    def shadow_enabled(cls, settings: Settings) -> bool:
        return settings.hermes_shadow_mode

    @classmethod
    def shadow_runtime_configured(cls, settings: Settings) -> bool:
        return bool(settings.hermes_shadow_api_url)

    @classmethod
    def for_pilot(cls, settings: Settings) -> "HermesService":
        pilot_settings = Settings(
            hermes_mode="real",
            hermes_api_url=settings.hermes_api_url or settings.hermes_shadow_api_url,
            hermes_api_key=settings.hermes_api_key,
            hermes_shadow_api_key=settings.hermes_shadow_api_key,
            hermes_timeout_seconds=settings.hermes_timeout_seconds,
        )
        return cls(settings=pilot_settings)

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

    def _safe_fallback_response(
        self, fallback_reason: str = "hermes_service_error"
    ) -> AgentResponse:
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
