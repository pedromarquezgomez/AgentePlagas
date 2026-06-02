from dataclasses import dataclass, field
from typing import Any

from app.config.settings import Settings
from app.schemas.agent_response import AgentResponse
from app.schemas.incoming_message import IncomingMessage
from app.schemas.tool_harness import ToolDecision, ToolExecutionRecord, ToolRequest
from experiments.nous_hermes_controlled.tool_harness import HermesToolHarness


@dataclass
class NousHermesPoCResult:
    agent_response: AgentResponse | None = None
    tool_requests: list[ToolRequest] = field(default_factory=list)
    tool_decisions: list[ToolDecision] = field(default_factory=list)
    execution_records: list[ToolExecutionRecord] = field(default_factory=list)


class NousHermesRuntimeAdapter:
    """Experimental adapter for controlled Nous Hermes output.

    It simulates the boundary we want from Nous Hermes: every output becomes an
    AgentResponse or a ToolRequest. ToolRequests are always passed through the
    harness and never executed in this PoC.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        harness: HermesToolHarness | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.harness = harness or HermesToolHarness(self.settings)

    async def process_message(
        self,
        incoming_message: IncomingMessage,
        *,
        trace_id: str,
        conversation_id: str,
    ) -> NousHermesPoCResult:
        raw_output = self._simulate_nous_hermes_output(
            incoming_message,
            trace_id=trace_id,
            conversation_id=conversation_id,
        )
        return self.normalize_output(raw_output)

    def normalize_output(self, raw_output: dict[str, Any]) -> NousHermesPoCResult:
        result = NousHermesPoCResult()

        if raw_output.get("agent_response"):
            result.agent_response = AgentResponse.model_validate(
                raw_output["agent_response"]
            )

        for item in raw_output.get("tool_requests", []):
            request = ToolRequest.model_validate(item)
            decision = self.harness.decide(request)
            record = self.harness.build_execution_record(request, decision)
            result.tool_requests.append(request)
            result.tool_decisions.append(decision)
            result.execution_records.append(record)

        return result

    def _simulate_nous_hermes_output(
        self,
        incoming_message: IncomingMessage,
        *,
        trace_id: str,
        conversation_id: str,
    ) -> dict[str, Any]:
        text = (incoming_message.text or "").lower()

        if "programa una visita" in text:
            return {
                "agent_response": {
                    "reply": (
                        "Puedo preparar la incidencia y dejar una propuesta de visita "
                        "para revisión interna."
                    ),
                    "action": {
                        "type": "create_incident",
                        "missing_fields": ["contact_phone", "exact_address"],
                    },
                    "incident": {
                        "should_create": True,
                        "pest_type": "cucarachas",
                        "location": "Torremolinos",
                        "affected_area": "cocina",
                        "priority": "high",
                        "summary": (
                            "Cliente solicita programar visita por cucarachas "
                            "en cocina en Torremolinos."
                        ),
                    },
                    "metadata": {
                        "source": "nous_hermes_controlled_poc",
                    },
                },
                "tool_requests": [
                    {
                        "tool_name": "incident.propose_incident",
                        "provider": "incident_service",
                        "action": "propose_incident",
                        "target": {"service": "IncidentService"},
                        "payload": {
                            "pest_type": "cucarachas",
                            "location": "Torremolinos",
                            "affected_area": "cocina",
                            "priority": "high",
                            "summary": (
                                "Propuesta de incidencia por cucarachas en cocina "
                                "en Torremolinos."
                            ),
                        },
                        "risk_level": 1,
                        "requires_approval": False,
                        "reason": (
                            "Proponer incidencia para que el backend decida; "
                            "no escribir Firestore desde Nous."
                        ),
                        "trace_id": trace_id,
                        "conversation_id": conversation_id,
                    },
                    {
                        "tool_name": "calendar.propose_event",
                        "provider": "calendar",
                        "action": "propose_event",
                        "target": {"calendar": "internal_visits"},
                        "payload": {
                            "window": "mañana por la mañana",
                            "reason": "Visita solicitada por el cliente",
                        },
                        "risk_level": 3,
                        "requires_approval": True,
                        "reason": "Proponer visita sin crear evento real.",
                        "trace_id": trace_id,
                        "conversation_id": conversation_id,
                    },
                    {
                        "tool_name": "telegram.draft_message",
                        "provider": incoming_message.channel,
                        "action": "draft_message",
                        "target": {"chat_id": incoming_message.external_chat_id},
                        "payload": {
                            "text": (
                                "Hemos preparado una propuesta de visita. "
                                "El equipo la revisará antes de confirmarla."
                            )
                        },
                        "risk_level": 3,
                        "requires_approval": True,
                        "reason": "Preparar borrador de respuesta sin enviarlo.",
                        "trace_id": trace_id,
                        "conversation_id": conversation_id,
                    },
                ],
            }

        if "whatsapp" in text and (
            "producto químico" in text
            or "producto quimico" in text
            or "fumigue" in text
            or "fumigar" in text
        ):
            return {
                "tool_requests": [
                    {
                        "tool_name": "whatsapp.draft_message",
                        "provider": "whatsapp",
                        "action": "draft_message",
                        "target": {"recipient": "cliente"},
                        "payload": {
                            "text": (
                                "Mensaje bloqueado: no se deben dar instrucciones "
                                "de fumigación ni productos químicos por WhatsApp."
                            ),
                            "safety_issue": "chemical_advice",
                        },
                        "risk_level": 5,
                        "requires_approval": True,
                        "reason": (
                            "El cliente pide enviar una instrucción peligrosa "
                            "sobre producto químico."
                        ),
                        "trace_id": trace_id,
                        "conversation_id": conversation_id,
                    }
                ]
            }

        if "envía un correo" in text or "envia un correo" in text:
            return {
                "tool_requests": [
                    {
                        "tool_name": "gmail.create_draft",
                        "provider": "gmail",
                        "action": "create_draft",
                        "target": {"recipient": "cliente"},
                        "payload": {
                            "subject": "Resumen del aviso",
                            "body": "Borrador de resumen operativo para revisión.",
                        },
                        "risk_level": 1,
                        "requires_approval": False,
                        "reason": "Crear propuesta de borrador, no enviar correo.",
                        "trace_id": trace_id,
                        "conversation_id": conversation_id,
                    }
                ]
            }

        return {
            "agent_response": {
                "reply": "Necesito más datos para preparar una propuesta controlada.",
                "action": {
                    "type": "collect_missing_data",
                    "missing_fields": ["intent"],
                },
                "incident": {"should_create": False},
                "metadata": {"source": "nous_hermes_controlled_poc"},
            }
        }
