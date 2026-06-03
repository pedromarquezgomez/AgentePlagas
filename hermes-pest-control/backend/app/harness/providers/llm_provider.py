import json
import logging
from typing import Any

import httpx
from pydantic import ValidationError

from app.config.settings import Settings
from app.context.contracts import ConversationContext
from app.harness.providers.mock_provider import MockAgentRuntimeProvider
from app.schemas.agent_response import AgentResponse

logger = logging.getLogger(__name__)


class LLMRuntimeProvider:
    name = "llm_provider"
    mode = "llm"
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.transport = transport
        self.fallback_provider = MockAgentRuntimeProvider()

    async def process(self, context: ConversationContext) -> AgentResponse:
        import time
        start_time = time.perf_counter()

        if self.settings.llm_provider.casefold() != "openai":
            return await self._fallback_to_mock(
                context,
                f"LLMProviderError:unsupported_provider:{self.settings.llm_provider}",
                start_time,
            )
        api_key = self._api_key()
        model = self._model()
        if not api_key:
            return await self._fallback_to_mock(context, "LLMProviderError:not_configured", start_time)
        if not model:
            return await self._fallback_to_mock(
                context,
                "LLMProviderError:model_not_configured",
                start_time,
            )

        payload = self._build_payload(context)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        trace_id = context.metadata.get("trace_id")

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds(),
                transport=self.transport,
            ) as client:
                response = await client.post(
                    self.endpoint,
                    json=payload,
                    headers=headers,
                )
        except httpx.TimeoutException as exc:
            logger.warning(
                "llm_runtime_request_failed trace_id=%s error_type=timeout "
                "error_class=%s",
                trace_id,
                exc.__class__.__name__,
            )
            return await self._fallback_to_mock(context, "LLMProviderError:timeout", start_time)
        except httpx.HTTPError as exc:
            logger.warning(
                "llm_runtime_request_failed trace_id=%s error_type=request_failed "
                "error_class=%s",
                trace_id,
                exc.__class__.__name__,
            )
            return await self._fallback_to_mock(
                context,
                "LLMProviderError:request_failed",
                start_time,
            )

        if response.status_code >= 400:
            logger.warning(
                "llm_runtime_request_failed trace_id=%s error_type=http_%s "
                "status_code=%s",
                trace_id,
                response.status_code,
                response.status_code,
            )
            return await self._fallback_to_mock(
                context,
                f"LLMProviderError:http_{response.status_code}",
                start_time,
            )

        try:
            response_json = response.json()
            response_text = self._extract_response_text(response_json)
            agent_response = AgentResponse.model_validate(json.loads(response_text))

            # Extraer tokens si el proveedor los devuelve
            usage = response_json.get("usage")
            tokens_used = None
            if isinstance(usage, dict):
                tokens_used = {
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                }

            latency_ms = (time.perf_counter() - start_time) * 1000.0

            from app.evaluation.runtime_stats import stats_collector
            stats_collector.record(
                provider="llm",
                model=model,
                latency_ms=latency_ms,
                fallback_used=False,
                tokens_used=tokens_used,
            )

            agent_response.metadata.update(
                {
                    "provider_used": "llm",
                    "model_used": model,
                    "fallback_used": False,
                    "latency_ms": latency_ms,
                    "tokens_used": tokens_used,
                }
            )
            return agent_response

        except (ValueError, ValidationError) as exc:
            logger.warning(
                "llm_runtime_response_invalid trace_id=%s error_class=%s",
                trace_id,
                exc.__class__.__name__,
            )
            return await self._fallback_to_mock(
                context,
                "LLMProviderError:invalid_response",
                start_time,
            )

    def _build_payload(self, context: ConversationContext) -> dict[str, Any]:
        business_context = {
            **context.metadata,
            "channel": context.channel,
            "user_id": context.user_id,
            "conversation_id": context.conversation_id,
            "incident_id": context.incident_id,
            "incident_summary": context.incident_summary,
            "policy_constraints": context.policy_constraints,
        }
        safe_runtime_payload = {
            "message": context.message.model_dump(mode="json"),
            "conversation_history": context.history,
            "business_context": business_context,
            "available_skills": [
                skill.model_dump(mode="json") for skill in context.available_skills
            ],
            "available_tools": [
                tool.as_runtime_metadata() for tool in context.available_tools
            ],
            "response_contract": "AgentResponse",
        }
        skill_sections = "\n\n".join(
            skill.as_prompt_section() for skill in context.available_skills
        )
        prompt = "\n\n".join(
            [
                "Return only strict JSON compatible with AgentResponse.",
                "You are Hermes Pest, a professional intake assistant for pest "
                "control incidents.",
                "You may reply to the client and propose actions, but you must never "
                "execute tools, write databases, send Telegram/WhatsApp, send email, "
                "or create calendar events.",
                "The backend is the only component allowed to execute tools after "
                "policy and controlled execution checks.",
                "Do not promise fixed visit times, guaranteed elimination, closed "
                "prices, or definitive diagnoses.",
                "Minimum data for creating an incident: pest type, affected area, "
                "location, and contact name when available. If essential data is "
                "missing, use collect_missing_data.",
                "For unknown pests or low confidence, use collect_missing_data or "
                "escalate_to_human and set metadata.requires_human_review when possible.",
                "If the user asks about dangerous chemicals, product mixing, exposure "
                "to pets/children/vulnerable people, or urgent health risk, escalate "
                "to human review and do not provide dangerous instructions.",
                "# Product Skills",
                skill_sections or "No product skills were provided.",
                "# Policy Constraints",
                json.dumps(
                    context.policy_constraints,
                    ensure_ascii=False,
                    indent=2,
                ),
                "# Backend Tools",
                json.dumps(
                    safe_runtime_payload["available_tools"],
                    ensure_ascii=False,
                    indent=2,
                ),
                json.dumps(safe_runtime_payload, ensure_ascii=False, indent=2),
            ]
        )
        return {
            "model": self._model(),
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are the controlled LLM runtime behind Hermes Pest "
                        "Harness. Return only JSON. External effects are forbidden. "
                        "All actions are proposals; backend services decide and execute."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "AgentResponse",
                    "strict": True,
                    "schema": self._agent_response_json_schema(),
                }
            },
            "max_output_tokens": self.settings.agent_max_output_tokens,
            "temperature": self.settings.agent_temperature,
        }

    def _extract_response_text(self, response_data: dict[str, Any]) -> str:
        output_text = response_data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        output = response_data.get("output")
        if isinstance(output, list):
            text_parts: list[str] = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for content_item in content:
                    if not isinstance(content_item, dict):
                        continue
                    text = content_item.get("text")
                    if isinstance(text, str):
                        text_parts.append(text)
            if text_parts:
                return "\n".join(text_parts)

        raise ValueError("LLM response did not include output text.")

    async def _fallback_to_mock(
        self,
        context: ConversationContext,
        fallback_reason: str,
        start_time: float,
    ) -> AgentResponse:
        if self.settings.llm_fallback_provider.casefold() != "mock":
            logger.warning(
                "llm_runtime_fallback_provider_unsupported trace_id=%s "
                "fallback_provider=%s",
                context.metadata.get("trace_id"),
                self.settings.llm_fallback_provider,
            )
        response = await self.fallback_provider.process(context)

        import time
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        try:
            model = self._model()
        except Exception:
            model = "unknown"

        from app.evaluation.runtime_stats import stats_collector
        stats_collector.record(
            provider="llm",
            model=model or "unknown",
            latency_ms=latency_ms,
            fallback_used=True,
        )

        response.metadata.update(
            {
                "fallback_used": True,
                "fallback_reason": fallback_reason,
                "fallback_provider": "mock",
                "llm_provider_failed": True,
                "effective_agent_provider": "mock",
                "provider_used": "mock",
                "model_used": model or "unknown",
                "latency_ms": latency_ms,
                "tokens_used": None,
            }
        )
        logger.info(
            "llm_runtime_fallback_to_mock trace_id=%s reason=%s",
            context.metadata.get("trace_id"),
            fallback_reason,
        )
        return response

    def _api_key(self) -> str:
        return (self.settings.llm_api_key or self.settings.openai_api_key).strip()

    def _model(self) -> str:
        return (self.settings.llm_model or self.settings.openai_model).strip()

    def _timeout_seconds(self) -> float:
        return self.settings.llm_timeout_seconds or self.settings.openai_timeout_seconds

    def _agent_response_json_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["reply", "action", "incident", "metadata"],
            "properties": {
                "reply": {"type": "string"},
                "action": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["type", "missing_fields"],
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": [
                                "reply_only",
                                "collect_missing_data",
                                "create_incident",
                                "escalate_to_human",
                            ],
                        },
                        "missing_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
                "incident": {
                    "anyOf": [
                        {"type": "null"},
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "should_create",
                                "pest_type",
                                "location",
                                "affected_area",
                                "priority",
                                "summary",
                                "id",
                                "conversation_id",
                                "status",
                            ],
                            "properties": {
                                "should_create": {"type": "boolean"},
                                "pest_type": {"type": ["string", "null"]},
                                "location": {"type": ["string", "null"]},
                                "affected_area": {"type": ["string", "null"]},
                                "priority": {
                                    "type": "string",
                                    "enum": ["low", "medium", "high", "urgent"],
                                },
                                "summary": {"type": ["string", "null"]},
                                "id": {"type": ["string", "null"]},
                                "conversation_id": {"type": ["string", "null"]},
                                "status": {"type": ["string", "null"]},
                            },
                        },
                    ]
                },
                "metadata": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {},
                },
            },
        }
