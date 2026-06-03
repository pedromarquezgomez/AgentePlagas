import json
import logging
from typing import Any

import httpx
from pydantic import ValidationError

from app.config.settings import Settings
from app.harness.contracts import AgentRuntimeRequest
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

    async def process(self, request: AgentRuntimeRequest) -> AgentResponse:
        if self.settings.llm_provider.casefold() != "openai":
            return self._safe_fallback_response(
                f"LLMProviderError:unsupported_provider:{self.settings.llm_provider}"
            )
        if not self.settings.openai_api_key:
            return self._safe_fallback_response("LLMProviderError:not_configured")
        if not self.settings.openai_model:
            return self._safe_fallback_response("LLMProviderError:model_not_configured")

        payload = self._build_payload(request)
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key.strip()}",
            "Content-Type": "application/json",
        }
        trace_id = request.business_context.get("trace_id")

        try:
            async with httpx.AsyncClient(
                timeout=self.settings.openai_timeout_seconds,
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
            return self._safe_fallback_response("LLMProviderError:timeout")
        except httpx.HTTPError as exc:
            logger.warning(
                "llm_runtime_request_failed trace_id=%s error_type=request_failed "
                "error_class=%s",
                trace_id,
                exc.__class__.__name__,
            )
            return self._safe_fallback_response("LLMProviderError:request_failed")

        if response.status_code >= 400:
            logger.warning(
                "llm_runtime_request_failed trace_id=%s error_type=http_%s "
                "status_code=%s",
                trace_id,
                response.status_code,
                response.status_code,
            )
            return self._safe_fallback_response(
                f"LLMProviderError:http_{response.status_code}"
            )

        try:
            response_text = self._extract_response_text(response.json())
            return AgentResponse.model_validate(json.loads(response_text))
        except (ValueError, ValidationError) as exc:
            logger.warning(
                "llm_runtime_response_invalid trace_id=%s error_class=%s",
                trace_id,
                exc.__class__.__name__,
            )
            return self._safe_fallback_response("LLMProviderError:invalid_response")

    def _build_payload(self, request: AgentRuntimeRequest) -> dict[str, Any]:
        safe_runtime_payload = {
            "message": request.incoming_message.model_dump(mode="json"),
            "conversation_history": request.conversation_history,
            "business_context": request.business_context,
            "available_skills": [
                skill.model_dump(mode="json") for skill in request.available_skills
            ],
            "available_tools": [
                tool.as_runtime_metadata() for tool in request.available_tools
            ],
            "response_contract": "AgentResponse",
        }
        skill_sections = "\n\n".join(
            skill.as_prompt_section() for skill in request.available_skills
        )
        prompt = "\n\n".join(
            [
                "Return only strict JSON compatible with AgentResponse.",
                "Do not call tools, databases, Telegram, WhatsApp, Gmail, or Calendar.",
                "Do not create incidents directly. Only propose a structured response.",
                "Tools are executable only by backend services after policy checks.",
                "# Product Skills",
                skill_sections or "No product skills were provided.",
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
            "model": self.settings.openai_model,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are the controlled LLM runtime behind Hermes Pest "
                        "Harness. Return only JSON. External effects are forbidden."
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

    def _safe_fallback_response(self, fallback_reason: str) -> AgentResponse:
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
