#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config.settings import Settings
from app.schemas.agent_response import AgentResponse

logger = logging.getLogger(__name__)

REQUIRED_SKILLS = [
    "02_pest_control_domain.md",
    "03_conversation_intake.md",
    "04_incident_lifecycle.md",
    "05_agent_response_contract.md",
    "06_human_escalation.md",
    "08_safety_and_compliance.md",
]

app = FastAPI(
    title="Hermes Agent Server",
    description="HTTP wrapper that exposes Hermes Agent through AgentResponse.",
)
settings = Settings()


class HermesAgentServerError(RuntimeError):
    pass


class HermesAgentConfigurationError(HermesAgentServerError):
    pass


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": settings.hermes_agent_mode}


@app.post("/agent")
async def agent(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        response = process_agent_request(payload, settings)
    except HermesAgentServerError as exc:
        logger.warning("hermes_agent_response_invalid error=%s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    logger.info(
        "hermes_agent_response_valid action_type=%s incident_should_create=%s",
        response.action.type,
        response.incident.should_create if response.incident else False,
    )
    return response.model_dump(mode="json")


def process_agent_request(
    payload: dict[str, Any],
    runtime_settings: Settings | None = None,
) -> AgentResponse:
    runtime_settings = runtime_settings or Settings()
    if payload.get("response_contract") != "AgentResponse":
        raise HermesAgentServerError("Unsupported response_contract.")

    system_prompt = load_system_prompt()
    skills_prompt = load_skills_prompt(runtime_settings.hermes_skills_dir)
    prompt = build_agent_prompt(payload, system_prompt, skills_prompt)
    raw_output = run_agent(prompt, payload, runtime_settings)
    return parse_agent_output(raw_output)


def load_system_prompt() -> str:
    prompt_path = BACKEND_DIR / "app" / "prompts" / "hermes_system_prompt.md"
    if not prompt_path.exists():
        raise HermesAgentServerError("Hermes system prompt is missing.")
    return prompt_path.read_text(encoding="utf-8")


def load_skills_prompt(skills_dir: str) -> str:
    resolved_dir = resolve_skills_dir(skills_dir)
    sections = []
    missing = []

    for skill_name in REQUIRED_SKILLS:
        skill_path = resolved_dir / skill_name
        if not skill_path.exists():
            missing.append(skill_name)
            continue
        sections.append(f"<!-- {skill_name} -->\n{skill_path.read_text(encoding='utf-8')}")

    if missing:
        raise HermesAgentServerError(
            f"Missing Hermes skills: {', '.join(sorted(missing))}."
        )

    logger.info(
        "hermes_agent_skills_loaded skills_count=%s skills_dir=%s",
        len(sections),
        resolved_dir,
    )
    return "\n\n".join(sections)


def resolve_skills_dir(skills_dir: str) -> Path:
    configured_path = Path(skills_dir).expanduser()
    if configured_path.is_absolute():
        return configured_path

    backend_dir = Path(__file__).resolve().parents[1]
    repo_root = backend_dir.parent
    candidates = [
        Path.cwd() / configured_path,
        backend_dir / configured_path,
        repo_root / configured_path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[1].resolve()


def build_agent_prompt(
    payload: dict[str, Any],
    system_prompt: str,
    skills_prompt: str,
) -> str:
    safe_payload = {
        "message": payload.get("message") or {},
        "conversation_history": payload.get("conversation_history") or [],
        "business_context": payload.get("business_context") or {},
        "response_contract": payload.get("response_contract"),
    }
    return "\n\n".join(
        [
            "# System Prompt",
            system_prompt,
            "# Skills",
            skills_prompt,
            "# Response Contract And Safety Rules",
            (
                "Return only strict JSON compatible with AgentResponse. Do not "
                "wrap the JSON in markdown. Do not write to databases, do not "
                "call Telegram or WhatsApp, do not schedule visits, and do not "
                "perform side effects. If the case involves safety, legal, "
                "medical, food-business risk, guarantees, pricing certainty, "
                "or unclear operational risk, use action.type="
                "escalate_to_human."
            ),
            "# Runtime Payload",
            json.dumps(safe_payload, ensure_ascii=False, indent=2),
        ]
    )


def run_agent(
    prompt: str,
    payload: dict[str, Any],
    runtime_settings: Settings,
) -> str:
    mode = runtime_settings.hermes_agent_mode.casefold()
    if mode in {"local", "fake"}:
        return run_local_skill_agent(payload, prompt)
    if mode == "llm":
        return run_llm_agent(prompt, runtime_settings)

    raise HermesAgentServerError(
        f"Unsupported HERMES_AGENT_MODE={runtime_settings.hermes_agent_mode!r}."
    )


def run_llm_agent(
    prompt: str,
    runtime_settings: Settings,
    transport: httpx.BaseTransport | None = None,
) -> str:
    if runtime_settings.llm_provider.casefold() != "openai":
        raise HermesAgentConfigurationError(
            f"Unsupported LLM_PROVIDER={runtime_settings.llm_provider!r}."
        )

    client = OpenAIResponsesClient(runtime_settings, transport=transport)
    return client.generate(prompt)


class OpenAIResponsesClient:
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(
        self,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.transport = transport

    def generate(self, prompt: str) -> str:
        if not self.settings.openai_api_key:
            raise HermesAgentConfigurationError("OPENAI_API_KEY is not configured.")
        if not self.settings.openai_model:
            raise HermesAgentConfigurationError("OPENAI_MODEL is not configured.")

        logger.info(
            "hermes_llm_request_started provider=%s model_configured=%s "
            "max_output_tokens=%s temperature=%s",
            self.settings.llm_provider,
            bool(self.settings.openai_model),
            self.settings.agent_max_output_tokens,
            self.settings.agent_temperature,
        )

        request_payload = {
            "model": self.settings.openai_model,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are a controlled business agent. Return only JSON "
                        "compatible with the provided AgentResponse contract. "
                        "Do not call tools, databases, Telegram, WhatsApp, or "
                        "any external system."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "AgentResponse",
                    "strict": True,
                    "schema": agent_response_json_schema(),
                }
            },
            "max_output_tokens": self.settings.agent_max_output_tokens,
            "temperature": self.settings.agent_temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(
                timeout=self.settings.openai_timeout_seconds,
                transport=self.transport,
            ) as client:
                response = client.post(
                    self.endpoint,
                    json=request_payload,
                    headers=headers,
                )
        except httpx.TimeoutException as exc:
            raise HermesAgentServerError("LLM request timed out.") from exc
        except httpx.HTTPError as exc:
            raise HermesAgentServerError("LLM request failed.") from exc

        if response.status_code >= 400:
            raise HermesAgentServerError(f"LLM returned HTTP {response.status_code}.")

        try:
            data = response.json()
        except ValueError as exc:
            raise HermesAgentServerError("LLM returned invalid JSON envelope.") from exc

        text = extract_openai_response_text(data)
        logger.info("hermes_llm_request_completed provider=%s", self.settings.llm_provider)
        return text


def agent_response_json_schema() -> dict[str, Any]:
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


def extract_openai_response_text(response_data: dict[str, Any]) -> str:
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

    raise HermesAgentServerError("LLM response did not include output text.")


def run_local_skill_agent(payload: dict[str, Any], prompt: str) -> str:
    # The prompt is intentionally built and passed in so this local adapter keeps
    # the same boundary a future model/CLI runtime will use.
    del prompt

    message = payload.get("message") or {}
    text = (message.get("text") or "").casefold()

    if _requires_human_review(text):
        return json.dumps(
            {
                "reply": (
                    "Gracias por avisarnos. Por seguridad, he dejado el caso para "
                    "que el equipo lo revise directamente."
                ),
                "action": {"type": "escalate_to_human", "missing_fields": []},
                "incident": {
                    "should_create": True,
                    "pest_type": _extract_pest_type(text),
                    "location": _extract_location(text),
                    "affected_area": _extract_affected_area(text),
                    "priority": "urgent" if _is_urgent_review(text) else "high",
                    "summary": "Caso sensible o de seguridad que requiere revisión humana.",
                },
            },
            ensure_ascii=False,
        )

    pest_type = _extract_pest_type(text)
    affected_area = _extract_affected_area(text)
    location = _extract_location(text)

    missing_fields = []
    if not pest_type:
        missing_fields.append("pest_type")
    if not affected_area:
        missing_fields.append("affected_area")
    if not location:
        missing_fields.append("location")

    if missing_fields:
        return json.dumps(
            {
                "reply": _build_missing_data_reply(missing_fields),
                "action": {
                    "type": "collect_missing_data",
                    "missing_fields": missing_fields,
                },
                "incident": {"should_create": False},
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "reply": (
                "Gracias por la información. He registrado el aviso para que el "
                "equipo lo revise."
            ),
            "action": {"type": "create_incident", "missing_fields": []},
            "incident": {
                "should_create": True,
                "pest_type": pest_type,
                "location": location,
                "affected_area": affected_area,
                "priority": "high" if pest_type in {"cucarachas", "roedores"} else "medium",
                "summary": (
                    f"Cliente informa de presencia de {pest_type} en "
                    f"{affected_area} en {location}."
                ),
            },
        },
        ensure_ascii=False,
    )


def parse_agent_output(raw_output: str | dict[str, Any]) -> AgentResponse:
    if isinstance(raw_output, dict):
        data = raw_output
    else:
        data = extract_json_object(raw_output)

    try:
        return AgentResponse.model_validate(data)
    except ValidationError as exc:
        raise HermesAgentServerError("Agent output violates AgentResponse.") from exc


def extract_json_object(raw_output: str) -> dict[str, Any]:
    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError:
        data = None

    if isinstance(data, dict):
        return data

    for candidate in _json_candidates(raw_output):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data

    raise HermesAgentServerError("Agent output does not contain valid JSON.")


def _json_candidates(raw_output: str) -> list[str]:
    candidates = []
    candidates.extend(
        match.group(1).strip()
        for match in re.finditer(r"```(?:json)?\s*(.*?)```", raw_output, re.DOTALL)
    )
    first_brace = raw_output.find("{")
    last_brace = raw_output.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidates.append(raw_output[first_brace : last_brace + 1])
    return candidates


def _requires_human_review(text: str) -> bool:
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
    )


def _is_urgent_review(text: str) -> bool:
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
            "industria alimentaria",
            "restaurante",
            "bar",
        ]
    )


def _extract_pest_type(text: str) -> str | None:
    if any(term in text for term in ["cucaracha", "cucarachas"]):
        return "cucarachas"
    if any(term in text for term in ["hormiga", "hormigas"]):
        return "hormigas"
    if any(
        term in text
        for term in [
            "roedor",
            "roedores",
            "rata",
            "ratas",
            "ratón",
            "raton",
            "ratones",
        ]
    ):
        return "roedores"
    return None


def _extract_affected_area(text: str) -> str | None:
    for area in [
        "cocina",
        "garaje",
        "baño",
        "bano",
        "jardín",
        "jardin",
        "almacén",
        "almacen",
    ]:
        if area in text:
            if area == "bano":
                return "baño"
            if area == "jardin":
                return "jardín"
            if area == "almacen":
                return "almacén"
            return area
    return None


def _extract_location(text: str) -> str | None:
    locations = {
        "torremolinos": "Torremolinos",
        "málaga": "Málaga",
        "malaga": "Málaga",
        "marbella": "Marbella",
        "fuengirola": "Fuengirola",
        "benalmádena": "Benalmádena",
        "benalmadena": "Benalmádena",
    }
    for raw, normalized in locations.items():
        if raw in text:
            return normalized
    return None


def _build_missing_data_reply(missing_fields: list[str]) -> str:
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="127.0.0.1", port=settings.hermes_agent_server_port)
