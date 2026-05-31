import logging
from uuid import uuid4

from app.schemas.agent_response import AgentResponse
from app.schemas.decision_record import DecisionRecordCreate
from app.schemas.human_review import HumanReviewItemCreate
from app.schemas.incoming_message import IncomingMessage
from app.schemas.incident import IncidentDraft
from app.services.decision_audit_service import DecisionAuditService
from app.services.firestore_factory import get_firestore_service
from app.services.hermes_clients import default_business_context
from app.services.hermes_service import HermesService
from app.services.human_review_service import HumanReviewService
from app.services.incident_service import IncidentService

logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(
        self,
        hermes_service: HermesService | None = None,
        incident_service: IncidentService | None = None,
        decision_audit_service: DecisionAuditService | None = None,
        human_review_service: HumanReviewService | None = None,
        firestore_service=None,
    ) -> None:
        self.hermes_service = hermes_service or HermesService()
        self.firestore_service = (
            firestore_service
            or getattr(incident_service, "firestore_service", None)
            or get_firestore_service()
        )
        self.incident_service = incident_service or IncidentService(self.firestore_service)
        self.decision_audit_service = decision_audit_service or DecisionAuditService(
            self.firestore_service
        )
        self.human_review_service = human_review_service or HumanReviewService(
            self.firestore_service
        )

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

        if self._should_create_incident(response):
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
        await self._store_outbound_message(message, conversation_id, trace_id, response)
        logger.info(
            "conversation_completed trace_id=%s conversation_id=%s action_type=%s",
            trace_id,
            conversation_id,
            response.action.type,
        )
        return response

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

        return IncidentDraft(
            conversation_id=conversation_id,
            channel=message.channel,
            pest_type=incident_data.pest_type if incident_data else None,
            location=incident_data.location if incident_data else None,
            affected_area=incident_data.affected_area if incident_data else None,
            priority=incident_data.priority if incident_data else "medium",
            summary=incident_data.summary if incident_data else None,
            metadata={
                "external_user_id": message.external_user_id,
                "external_chat_id": message.external_chat_id,
                "source_message_type": message.message_type,
                "source_metadata": message.metadata,
            },
        )

    async def _get_hermes_response(
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
            hermes_mode=getattr(self.hermes_service, "hermes_mode", "unknown"),
            action_type=response.action.type,
            incident_should_create=incident_should_create,
            pest_type=response.incident.pest_type if response.incident else None,
            priority=response.incident.priority if response.incident else None,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            metadata={
                "message_type": message.message_type,
                "missing_fields": response.action.missing_fields,
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
