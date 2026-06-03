import logging
import random
from typing import Callable
from uuid import uuid4

from app.config.settings import Settings
from app.schemas.agent_response import AgentResponse
from app.schemas.decision_record import DecisionRecordCreate
from app.schemas.human_review import HumanReviewItemCreate
from app.schemas.incoming_message import IncomingMessage
from app.schemas.incident import IncidentDraft
from app.schemas.pilot_gate import PilotGateResult
from app.schemas.shadow_decision_record import ShadowDecisionRecordCreate
from app.services.decision_audit_service import DecisionAuditService
from app.services.firestore_factory import get_firestore_service
from app.services.hermes_clients import default_business_context
from app.services.hermes_service import HermesService
from app.services.human_review_service import HumanReviewService
from app.services.incident_service import IncidentService
from app.services.pilot_gate import HermesPilotGate
from app.services.shadow_decision_service import ShadowDecisionService

logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(
        self,
        hermes_service: HermesService | None = None,
        incident_service: IncidentService | None = None,
        decision_audit_service: DecisionAuditService | None = None,
        human_review_service: HumanReviewService | None = None,
        shadow_decision_service: ShadowDecisionService | None = None,
        shadow_hermes_service: HermesService | None = None,
        pilot_hermes_service: HermesService | None = None,
        pilot_gate: HermesPilotGate | None = None,
        firestore_service=None,
        settings: Settings | None = None,
        random_func: Callable[[], float] | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.firestore_service = (
            firestore_service
            or getattr(incident_service, "firestore_service", None)
            or get_firestore_service()
        )
        if hermes_service is None:
            from app.context.manager import ContextManager
            from app.policies.engine import PolicyEngine
            policy_engine = PolicyEngine()
            ctx_manager = ContextManager(
                firestore_service=self.firestore_service,
                policy_engine=policy_engine,
                settings=self.settings,
            )
            self.hermes_service = HermesService(
                settings=self.settings,
                context_manager=ctx_manager,
            )
        else:
            self.hermes_service = hermes_service
        self.incident_service = incident_service or IncidentService(self.firestore_service)
        self.decision_audit_service = decision_audit_service or DecisionAuditService(
            self.firestore_service
        )
        self.human_review_service = human_review_service or HumanReviewService(
            self.firestore_service
        )
        self.shadow_decision_service = shadow_decision_service or ShadowDecisionService(
            self.firestore_service
        )
        self.shadow_hermes_service = shadow_hermes_service
        self.pilot_hermes_service = pilot_hermes_service
        self.pilot_gate = pilot_gate or HermesPilotGate()
        self.random_func = random_func or random.random

        from app.services.tool_execution_service import ToolExecutionService
        from app.policies.engine import PolicyEngine
        from app.audit.service import default_audit_service

        self.tool_execution_service = ToolExecutionService(self.firestore_service)
        self.policy_engine = PolicyEngine()
        self.audit_service = default_audit_service()

    async def handle_incoming_message(self, message: IncomingMessage) -> AgentResponse:
        trace_id = self.build_trace_id()
        conversation_id = self.build_conversation_id(message)
        logger.info(
            "conversation_started trace_id=%s channel=%s conversation_id=%s",
            trace_id,
            message.channel,
            conversation_id,
        )
        await self._upsert_conversation(message, conversation_id)
        inbound_message = await self._store_inbound_message(
            message,
            conversation_id,
            trace_id,
        )

        response = await self._get_hermes_response(message, conversation_id, trace_id)
        incident_id = None

        if response.action.type == "create_incident":
            incident_id = await self._execute_create_incident_tool(
                message=message,
                conversation_id=conversation_id,
                trace_id=trace_id,
                response=response,
            )
        elif self._should_create_incident(response):
            incident = self._build_incident(message, conversation_id, response)
            created_incident = await self.incident_service.create_incident(incident)
            incident_id = created_incident.id
            if response.incident is not None:
                response.incident.id = created_incident.id
                response.incident.conversation_id = created_incident.conversation_id
                response.incident.status = created_incident.status

        decision_record = await self._record_decision(
            message=message,
            conversation_id=conversation_id,
            trace_id=trace_id,
            message_id=inbound_message.get("id"),
            incident_id=incident_id,
            response=response,
        )
        await self._create_human_review_item_if_needed(
            message=message,
            conversation_id=conversation_id,
            trace_id=trace_id,
            incident_id=incident_id,
            decision_record_id=decision_record.id,
            response=response,
        )
        await self._run_shadow_if_enabled(
            message=message,
            conversation_id=conversation_id,
            trace_id=trace_id,
            primary_response=response,
        )
        # Registrar evento de priorización en auditoría al final si existe assessment real
        if response.incident and response.incident.severity:
            from app.audit.contracts import AuditEvent, AuditEventType
            self.audit_service.record_event(
                AuditEvent(
                    event_type=AuditEventType.INCIDENT_PRIORITIZED,
                    execution_id=trace_id,
                    user_id=message.external_user_id,
                    channel=message.channel,
                    status="completed",
                    message="Incident prioritization completed.",
                    metadata={
                        "severity": response.incident.severity,
                        "priority": response.incident.priority,
                        "reason": response.incident.assessment_reason,
                        "response_hours": response.incident.response_hours,
                    },
                )
            )

        await self._store_outbound_message(message, conversation_id, trace_id, response)

        logger.info(
            "conversation_completed trace_id=%s conversation_id=%s action_type=%s",
            trace_id,
            conversation_id,
            response.action.type,
        )
        return response

    async def _execute_create_incident_tool(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        response: AgentResponse,
    ) -> str | None:
        from app.schemas.tool_harness import ToolExecutionRecord
        from app.policies.contracts import PolicyContext, PolicyDecision
        from app.audit.contracts import AuditEvent, AuditEventType

        tool_name = "create_incident_tool"
        tool_request_id = str(uuid4())
        tool_decision_id = str(uuid4())
        execution_id = str(uuid4())

        tool_payload = {
            "conversation_id": conversation_id,
            "channel": message.channel,
            "pest_type": response.incident.pest_type if response.incident else None,
            "location": response.incident.location if response.incident else None,
            "affected_area": response.incident.affected_area if response.incident else None,
            "priority": response.incident.priority if response.incident else "medium",
            "summary": response.incident.summary if response.incident else None,
            "metadata": {
                "customer_name": response.metadata.get("customer_name")
                or (getattr(response.incident, "metadata", {}) or {}).get("customer_name")
                if response.incident else None,
                "confidence": getattr(response.incident, "confidence", None) if response.incident else None,
                "evidence": getattr(response.incident, "evidence", None) if response.incident else None,
                "detected_terms": getattr(response.incident, "detected_terms", []) if response.incident else [],
                "severity": getattr(response.incident, "severity", None) if response.incident else None,
                "priority": getattr(response.incident, "priority", None) if response.incident else None,
                "response_hours": getattr(response.incident, "response_hours", None) if response.incident else None,
                "assessment_reason": getattr(response.incident, "assessment_reason", None) if response.incident else None,
                "classification": {
                    "pest_type": response.incident.pest_type if response.incident else None,
                    "confidence": getattr(response.incident, "confidence", None) if response.incident else None,
                    "evidence": getattr(response.incident, "evidence", None) if response.incident else None,
                    "detected_terms": getattr(response.incident, "detected_terms", []) if response.incident else [],
                } if response.incident else None,
                **(response.metadata if response.metadata else {}),
            }
        }

        self.audit_service.record_event(
            AuditEvent(
                event_type=AuditEventType.TOOL_PROPOSED,
                execution_id=execution_id,
                tool_name=tool_name,
                provider="mock_provider",
                user_id=message.external_user_id,
                channel=message.channel,
                status="requested",
                message="Tool execution requested.",
                metadata={
                    "action": "create_incident",
                    "risk_level": 2,
                    "requires_approval": False,
                },
            )
        )

        policy_context = PolicyContext(
            channel=message.channel,
            user_id=message.external_user_id,
            requested_tool=tool_name,
            requested_action="create_incident",
            source_provider="mock_provider",
        )
        policy_result = self.policy_engine.evaluate(policy_context)

        self.audit_service.record_event(
            AuditEvent(
                event_type=AuditEventType.POLICY_EVALUATED,
                execution_id=execution_id,
                tool_name=tool_name,
                provider="mock_provider",
                user_id=message.external_user_id,
                channel=message.channel,
                policy_decision=policy_result.decision.value,
                status=policy_result.decision.value,
                message="Policy Engine evaluated tool execution.",
                metadata={"action": "create_incident"},
            )
        )

        record = ToolExecutionRecord(
            id=execution_id,
            tool_request_id=tool_request_id,
            tool_decision_id=tool_decision_id,
            trace_id=trace_id,
            conversation_id=conversation_id,
            tool_name=tool_name,
            provider="mock_provider",
            action="create_incident",
            risk_level=2,
            requires_approval=False,
            decision="allow" if policy_result.decision == PolicyDecision.ALLOW else "deny",
            execution_status="allowed_not_executed" if policy_result.decision == PolicyDecision.ALLOW else "blocked",
            review_status="approved" if policy_result.decision == PolicyDecision.ALLOW else "dismissed",
            approved_payload=tool_payload,
            metadata={"payload": tool_payload},
        )
        await self.tool_execution_service.create_execution_record(record)

        incident_id = None
        if policy_result.decision == PolicyDecision.ALLOW:
            execute_fn = getattr(self.tool_execution_service, "execute_execution_record")
            execution_record = await execute_fn(execution_id)
            created_incident_data = execution_record.get("execution_result")
            if created_incident_data:
                incident_id = created_incident_data.get("id")
                if response.incident is not None:
                    response.incident.id = incident_id
                    response.incident.conversation_id = conversation_id
                    response.incident.status = created_incident_data.get("status")
        return incident_id

    def build_conversation_id(self, message: IncomingMessage) -> str:
        return f"{message.channel}:{message.external_user_id}"

    def build_trace_id(self) -> str:
        return str(uuid4())

    def _should_create_incident(self, response: AgentResponse) -> bool:
        return (
            response.action.type in {"create_incident", "escalate_to_human"}
            and bool(response.incident)
            and response.incident.should_create
        )

    def _build_incident(
        self,
        message: IncomingMessage,
        conversation_id: str,
        response: AgentResponse,
    ) -> IncidentDraft:
        incident_data = response.incident

        metadata = {
            "external_user_id": message.external_user_id,
            "external_chat_id": message.external_chat_id,
            "source_message_type": message.message_type,
            "source_metadata": message.metadata,
        }
        if incident_data:
            if getattr(incident_data, "confidence", None):
                metadata["confidence"] = incident_data.confidence
            if getattr(incident_data, "evidence", None):
                metadata["evidence"] = incident_data.evidence
            if getattr(incident_data, "detected_terms", None):
                metadata["detected_terms"] = incident_data.detected_terms
            if getattr(incident_data, "severity", None):
                metadata["severity"] = incident_data.severity
            if getattr(incident_data, "response_hours", None):
                metadata["response_hours"] = incident_data.response_hours
            if getattr(incident_data, "assessment_reason", None):
                metadata["assessment_reason"] = incident_data.assessment_reason

            metadata["classification"] = {
                "pest_type": incident_data.pest_type,
                "confidence": getattr(incident_data, "confidence", None),
                "evidence": getattr(incident_data, "evidence", None),
                "detected_terms": getattr(incident_data, "detected_terms", []),
            }

        return IncidentDraft(
            conversation_id=conversation_id,
            channel=message.channel,
            pest_type=incident_data.pest_type if incident_data else None,
            location=incident_data.location if incident_data else None,
            affected_area=incident_data.affected_area if incident_data else None,
            priority=incident_data.priority if incident_data else "medium",
            summary=incident_data.summary if incident_data else None,
            metadata=metadata,
        )

    async def _get_hermes_response(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
    ) -> AgentResponse:
        if self._is_pilot_candidate(message):
            return await self._get_pilot_or_fallback_response(
                message,
                conversation_id,
                trace_id,
            )

        if self.settings.hermes_pilot_mode:
            logger.info(
                "hermes_pilot_skipped trace_id=%s conversation_id=%s reason=channel",
                trace_id,
                conversation_id,
            )
        try:
            business_context = default_business_context(conversation_id)
            business_context["trace_id"] = trace_id
            raw_response = await self.hermes_service.process_message(
                message,
                conversation_history=[],
                business_context=business_context,
            )
            if isinstance(raw_response, AgentResponse):
                return raw_response
            return AgentResponse.model_validate(raw_response)
        except Exception:
            return self._build_safe_agent_error_response()

    async def _get_pilot_or_fallback_response(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
    ) -> AgentResponse:
        gate_result = self.pilot_gate.evaluate(message)
        if not gate_result.eligible:
            if gate_result.route == "human_review":
                logger.info(
                    "hermes_pilot_blocked trace_id=%s conversation_id=%s route=%s "
                    "policy_rule=%s",
                    trace_id,
                    conversation_id,
                    gate_result.route,
                    gate_result.policy_rule,
                )
                return self._build_pilot_human_review_response(gate_result)

            response = await self._get_primary_hermes_response(
                message,
                conversation_id,
                trace_id,
            )
            self._merge_metadata(
                response,
                self._pilot_metadata(
                    gate_result=gate_result,
                    pilot_used=False,
                    pilot_blocked=True,
                ),
            )
            return response

        if not self._should_sample_pilot():
            response = await self._get_primary_hermes_response(
                message,
                conversation_id,
                trace_id,
            )
            self._merge_metadata(
                response,
                self._pilot_metadata(
                    gate_result=gate_result,
                    pilot_used=False,
                    pilot_blocked=True,
                    extra={"pilot_blocked_reason": "sample_rate"},
                ),
            )
            return response

        try:
            pilot_service = self.pilot_hermes_service or self._build_pilot_hermes_service()
            business_context = default_business_context(conversation_id)
            business_context["trace_id"] = trace_id
            business_context["pilot_mode"] = True
            raw_response = await pilot_service.process_message(
                message,
                conversation_history=[],
                business_context=business_context,
            )
            response = (
                raw_response
                if isinstance(raw_response, AgentResponse)
                else AgentResponse.model_validate(raw_response)
            )
            if bool(response.metadata.get("fallback_used", False)):
                return await self._pilot_fallback_to_primary(
                    message,
                    conversation_id,
                    trace_id,
                    gate_result,
                    response.metadata.get("fallback_reason") or "agent_fallback",
                )
            if len(response.reply or "") > self.settings.hermes_pilot_max_response_length:
                return await self._pilot_fallback_to_primary(
                    message,
                    conversation_id,
                    trace_id,
                    gate_result,
                    "max_response_length",
                )
            self._merge_metadata(
                response,
                self._pilot_metadata(
                    gate_result=gate_result,
                    pilot_used=True,
                    pilot_blocked=False,
                    extra={
                        "effective_hermes_mode": "pilot",
                        "pilot_agent_hermes_mode": getattr(
                            pilot_service,
                            "hermes_mode",
                            "real",
                        ),
                    },
                ),
            )
            logger.info(
                "hermes_pilot_used trace_id=%s conversation_id=%s action_type=%s",
                trace_id,
                conversation_id,
                response.action.type,
            )
            return response
        except Exception as exc:
            return await self._pilot_fallback_to_primary(
                message,
                conversation_id,
                trace_id,
                gate_result,
                f"UnexpectedError:{exc.__class__.__name__}",
            )

    async def _get_primary_hermes_response(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
    ) -> AgentResponse:
        try:
            business_context = default_business_context(conversation_id)
            business_context["trace_id"] = trace_id
            raw_response = await self.hermes_service.process_message(
                message,
                conversation_history=[],
                business_context=business_context,
            )
            if isinstance(raw_response, AgentResponse):
                return raw_response
            return AgentResponse.model_validate(raw_response)
        except Exception:
            return self._build_safe_agent_error_response()

    async def _pilot_fallback_to_primary(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        gate_result: PilotGateResult,
        fallback_reason: str,
    ) -> AgentResponse:
        logger.warning(
            "hermes_pilot_fallback trace_id=%s conversation_id=%s reason=%s",
            trace_id,
            conversation_id,
            fallback_reason,
        )
        response = await self._get_primary_hermes_response(
            message,
            conversation_id,
            trace_id,
        )
        self._merge_metadata(
            response,
            self._pilot_metadata(
                gate_result=gate_result,
                pilot_used=False,
                pilot_blocked=False,
                extra={
                    "fallback_used": True,
                    "fallback_reason": str(fallback_reason),
                    "pilot_agent_failed": True,
                },
            ),
        )
        return response

    def _build_pilot_human_review_response(
        self,
        gate_result: PilotGateResult,
    ) -> AgentResponse:
        return AgentResponse(
            reply=(
                "Gracias por avisarnos. Por seguridad, voy a pasar este caso al "
                "equipo para que lo revise antes de darte indicaciones."
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
                "priority": "urgent",
                "summary": (
                    "Caso bloqueado por Pilot Gate. Requiere revisión humana antes "
                    "de delegar en Hermes Agent."
                ),
            },
            metadata=self._pilot_metadata(
                gate_result=gate_result,
                pilot_used=False,
                pilot_blocked=True,
                extra={"sensitive_case": True},
            ),
        )

    def _pilot_metadata(
        self,
        gate_result: PilotGateResult,
        pilot_used: bool,
        pilot_blocked: bool,
        extra: dict | None = None,
    ) -> dict:
        metadata = {
            "pilot_mode": True,
            "pilot_used": pilot_used,
            "pilot_blocked": pilot_blocked,
            "pilot_gate_eligible": gate_result.eligible,
            "pilot_route": gate_result.route,
            "pilot_blocked_reason": gate_result.reason if pilot_blocked else None,
            "pilot_risk_flags": gate_result.risk_flags,
            "pilot_policy_rule": gate_result.policy_rule,
        }
        if extra:
            metadata.update(extra)
        return metadata

    def _merge_metadata(self, response: AgentResponse, metadata: dict) -> None:
        response.metadata.update(
            {key: value for key, value in metadata.items() if value is not None}
        )

    def _is_pilot_candidate(self, message: IncomingMessage) -> bool:
        if not self.settings.hermes_pilot_mode:
            return False
        allowed_channels = {
            channel.strip()
            for channel in self.settings.hermes_pilot_allowed_channels.split(",")
            if channel.strip()
        }
        if allowed_channels and message.channel not in allowed_channels:
            return False
        return True

    def _should_sample_pilot(self) -> bool:
        sample_rate = max(0.0, min(1.0, self.settings.hermes_pilot_sample_rate))
        return self.random_func() < sample_rate

    def _build_pilot_hermes_service(self) -> HermesService:
        return HermesService.for_pilot(self.settings)

    def _build_safe_agent_error_response(self) -> AgentResponse:
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
                "fallback_reason": "conversation_service_invalid_agent_response",
            },
        )

    async def _upsert_conversation(
        self,
        message: IncomingMessage,
        conversation_id: str,
    ) -> None:
        existing_conversation = await self.firestore_service.get_document(
            "conversations",
            conversation_id,
        )
        conversation_data = {
            "id": conversation_id,
            "channel": message.channel,
            "external_user_id": message.external_user_id,
            "external_chat_id": message.external_chat_id,
            "status": "active",
        }

        if existing_conversation is None:
            await self.firestore_service.create_document(
                "conversations",
                conversation_data,
                document_id=conversation_id,
            )
            return

        await self.firestore_service.update_document(
            "conversations",
            conversation_id,
            conversation_data,
        )

    async def _store_inbound_message(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
    ) -> dict:
        return await self.firestore_service.create_document(
            "messages",
            {
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "direction": "inbound",
                "channel": message.channel,
                "text": message.text,
                "attachments": message.attachments,
                "metadata": message.metadata,
            },
        )

    async def _store_outbound_message(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        response: AgentResponse,
    ) -> None:
        await self.firestore_service.create_document(
            "messages",
            {
                "conversation_id": conversation_id,
                "trace_id": trace_id,
                "direction": "outbound",
                "channel": message.channel,
                "text": response.reply,
                "attachments": [],
                "metadata": {},
            },
        )

    async def _record_decision(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        message_id: str | None,
        incident_id: str | None,
        response: AgentResponse,
    ):
        incident_should_create = (
            response.incident.should_create if response.incident is not None else False
        )
        fallback_used = bool(response.metadata.get("fallback_used", False))
        fallback_reason = response.metadata.get("fallback_reason")
        decision_record = DecisionRecordCreate(
            trace_id=trace_id,
            conversation_id=conversation_id,
            message_id=message_id,
            incident_id=incident_id,
            channel=message.channel,
            hermes_mode=response.metadata.get(
                "effective_hermes_mode",
                getattr(self.hermes_service, "hermes_mode", "unknown"),
            ),
            action_type=response.action.type,
            incident_should_create=incident_should_create,
            pest_type=response.incident.pest_type if response.incident else None,
            priority=response.incident.priority if response.incident else None,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            pilot_mode_enabled=bool(response.metadata.get("pilot_mode", False)),
            pilot_used=bool(response.metadata.get("pilot_used", False)),
            pilot_blocked=bool(response.metadata.get("pilot_blocked", False)),
            pilot_blocked_reason=response.metadata.get("pilot_blocked_reason"),
            pilot_route=response.metadata.get("pilot_route"),
            pilot_risk_flags=response.metadata.get("pilot_risk_flags", []),
            pilot_policy_rule=response.metadata.get("pilot_policy_rule"),
            metadata={
                "message_type": message.message_type,
                "missing_fields": response.action.missing_fields,
                "pilot_mode": bool(response.metadata.get("pilot_mode", False)),
                "pilot_used": bool(response.metadata.get("pilot_used", False)),
                "pilot_blocked": bool(response.metadata.get("pilot_blocked", False)),
                "pilot_gate_eligible": response.metadata.get("pilot_gate_eligible"),
                "pilot_route": response.metadata.get("pilot_route"),
                "pilot_blocked_reason": response.metadata.get("pilot_blocked_reason"),
                "pilot_risk_flags": response.metadata.get("pilot_risk_flags", []),
                "pilot_policy_rule": response.metadata.get("pilot_policy_rule"),
                "pilot_agent_failed": bool(
                    response.metadata.get("pilot_agent_failed", False)
                ),
            },
        )
        created_decision_record = (
            await self.decision_audit_service.create_decision_record(decision_record)
        )
        logger.info(
            "decision_record_created trace_id=%s conversation_id=%s action_type=%s "
            "fallback_used=%s",
            trace_id,
            conversation_id,
            response.action.type,
            fallback_used,
        )
        return created_decision_record

    async def _create_human_review_item_if_needed(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        incident_id: str | None,
        decision_record_id: str | None,
        response: AgentResponse,
    ) -> None:
        reasons = self._human_review_reasons(response)
        if not reasons:
            return

        priority = response.incident.priority if response.incident else "medium"
        summary = (
            response.incident.summary
            if response.incident and response.incident.summary
            else response.reply
        )
        review_item = HumanReviewItemCreate(
            trace_id=trace_id,
            conversation_id=conversation_id,
            incident_id=incident_id,
            decision_record_id=decision_record_id,
            channel=message.channel,
            reason=reasons[0],
            priority=priority,
            summary=summary,
            metadata={
                "review_reasons": reasons,
                "action_type": response.action.type,
                "fallback_reason": response.metadata.get("fallback_reason"),
                "missing_fields": response.action.missing_fields,
            },
        )
        created_review_item = await self.human_review_service.create_review_item(
            review_item
        )
        logger.info(
            "human_review_item_created trace_id=%s conversation_id=%s review_item_id=%s "
            "reason=%s priority=%s",
            trace_id,
            conversation_id,
            created_review_item.id,
            reasons[0],
            priority,
        )

    def _human_review_reasons(self, response: AgentResponse) -> list[str]:
        reasons = []
        fallback_used = bool(response.metadata.get("fallback_used", False))
        priority = response.incident.priority if response.incident else None

        if fallback_used:
            reasons.append("fallback_used")
        if response.action.type == "escalate_to_human":
            reasons.append("agent_escalation")
        if priority == "urgent":
            reasons.append("urgent_priority")
        if response.metadata.get("sensitive_case") is True:
            reasons.append("sensitive_case")

        return reasons

    async def _run_shadow_if_enabled(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        primary_response: AgentResponse,
    ) -> None:
        if not HermesService.shadow_enabled(self.settings):
            return
        if (
            self.shadow_hermes_service is None
            and not HermesService.shadow_runtime_configured(self.settings)
        ):
            logger.warning(
                "hermes_shadow_skipped trace_id=%s conversation_id=%s "
                "reason=missing_shadow_api_url",
                trace_id,
                conversation_id,
            )
            return
        if not self._should_sample_shadow():
            logger.info(
                "hermes_shadow_skipped trace_id=%s conversation_id=%s reason=sample_rate",
                trace_id,
                conversation_id,
            )
            return

        shadow_service = self.shadow_hermes_service or self._build_shadow_hermes_service()
        business_context = default_business_context(conversation_id)
        business_context["trace_id"] = trace_id
        business_context["shadow_mode"] = True

        shadow_response: AgentResponse | None = None
        shadow_error: str | None = None
        shadow_fallback_reason: str | None = None

        try:
            raw_shadow_response = await shadow_service.process_message(
                message,
                conversation_history=[],
                business_context=business_context,
            )
            shadow_response = (
                raw_shadow_response
                if isinstance(raw_shadow_response, AgentResponse)
                else AgentResponse.model_validate(raw_shadow_response)
            )
            if bool(shadow_response.metadata.get("fallback_used", False)):
                shadow_fallback_reason = str(
                    shadow_response.metadata.get("fallback_reason")
                    or "HermesClientError:unknown"
                )
                shadow_error = shadow_fallback_reason
        except Exception as exc:
            shadow_error = f"UnexpectedError:{exc.__class__.__name__}"
            logger.warning(
                "hermes_shadow_error trace_id=%s conversation_id=%s error=%s",
                trace_id,
                conversation_id,
                shadow_error,
            )

        await self.shadow_decision_service.create_shadow_record(
            self._build_shadow_record(
                message=message,
                conversation_id=conversation_id,
                trace_id=trace_id,
                primary_response=primary_response,
                shadow_response=shadow_response,
                shadow_error=shadow_error,
                shadow_fallback_reason=shadow_fallback_reason,
                shadow_hermes_mode=getattr(shadow_service, "hermes_mode", "real"),
            )
        )
        logger.info(
            "hermes_shadow_record_created trace_id=%s conversation_id=%s "
            "primary_action=%s shadow_action=%s shadow_error=%s",
            trace_id,
            conversation_id,
            primary_response.action.type,
            shadow_response.action.type if shadow_response else None,
            shadow_error,
        )

    def _should_sample_shadow(self) -> bool:
        sample_rate = max(0.0, min(1.0, self.settings.hermes_shadow_sample_rate))
        return self.random_func() < sample_rate

    def _build_shadow_hermes_service(self) -> HermesService:
        return HermesService.for_shadow(self.settings)

    def _build_shadow_record(
        self,
        message: IncomingMessage,
        conversation_id: str,
        trace_id: str,
        primary_response: AgentResponse,
        shadow_response: AgentResponse | None,
        shadow_error: str | None,
        shadow_fallback_reason: str | None,
        shadow_hermes_mode: str,
    ) -> ShadowDecisionRecordCreate:
        differences = self._compare_shadow_response(primary_response, shadow_response)
        return ShadowDecisionRecordCreate(
            trace_id=trace_id,
            conversation_id=conversation_id,
            channel=message.channel,
            primary_hermes_mode=getattr(self.hermes_service, "hermes_mode", "unknown"),
            shadow_hermes_mode=shadow_hermes_mode,
            primary_action_type=primary_response.action.type,
            shadow_action_type=shadow_response.action.type if shadow_response else None,
            primary_priority=(
                primary_response.incident.priority if primary_response.incident else None
            ),
            shadow_priority=(
                shadow_response.incident.priority
                if shadow_response and shadow_response.incident
                else None
            ),
            primary_pest_type=(
                primary_response.incident.pest_type if primary_response.incident else None
            ),
            shadow_pest_type=(
                shadow_response.incident.pest_type
                if shadow_response and shadow_response.incident
                else None
            ),
            primary_should_create=(
                primary_response.incident.should_create
                if primary_response.incident
                else False
            ),
            shadow_should_create=(
                shadow_response.incident.should_create
                if shadow_response and shadow_response.incident
                else None
            ),
            agreement_summary=self._agreement_summary(differences, shadow_error),
            differences=differences,
            shadow_fallback_used=(
                bool(shadow_response.metadata.get("fallback_used", False))
                if shadow_response
                else False
            ),
            shadow_error=shadow_error,
            metadata={
                "message_type": message.message_type,
                "primary_missing_fields": primary_response.action.missing_fields,
                "shadow_missing_fields": (
                    shadow_response.action.missing_fields if shadow_response else []
                ),
                "shadow_fallback_reason": shadow_fallback_reason,
            },
        )

    def _compare_shadow_response(
        self,
        primary_response: AgentResponse,
        shadow_response: AgentResponse | None,
    ) -> dict:
        if shadow_response is None:
            return {"shadow_response": {"primary": "present", "shadow": None}}

        comparisons = {
            "action_type": (
                primary_response.action.type,
                shadow_response.action.type,
            ),
            "priority": (
                primary_response.incident.priority if primary_response.incident else None,
                shadow_response.incident.priority if shadow_response.incident else None,
            ),
            "pest_type": (
                primary_response.incident.pest_type if primary_response.incident else None,
                shadow_response.incident.pest_type if shadow_response.incident else None,
            ),
            "should_create": (
                primary_response.incident.should_create
                if primary_response.incident
                else False,
                shadow_response.incident.should_create
                if shadow_response.incident
                else False,
            ),
        }
        return {
            field: {"primary": primary, "shadow": shadow}
            for field, (primary, shadow) in comparisons.items()
            if primary != shadow
        }

    def _agreement_summary(self, differences: dict, shadow_error: str | None) -> str:
        if shadow_error:
            return "shadow_error"
        if not differences:
            return "full_agreement"
        return "differences_detected"
