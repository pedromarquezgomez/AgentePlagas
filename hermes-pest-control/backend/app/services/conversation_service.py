from app.schemas.agent_response import AgentResponse
from app.schemas.incoming_message import IncomingMessage
from app.schemas.incident import IncidentDraft
from app.services.firestore_factory import get_firestore_service
from app.services.hermes_service import HermesService
from app.services.incident_service import IncidentService


class ConversationService:
    def __init__(
        self,
        hermes_service: HermesService | None = None,
        incident_service: IncidentService | None = None,
        firestore_service=None,
    ) -> None:
        self.hermes_service = hermes_service or HermesService()
        self.firestore_service = (
            firestore_service
            or getattr(incident_service, "firestore_service", None)
            or get_firestore_service()
        )
        self.incident_service = incident_service or IncidentService(self.firestore_service)

    async def handle_incoming_message(self, message: IncomingMessage) -> AgentResponse:
        conversation_id = self.build_conversation_id(message)
        await self._upsert_conversation(message, conversation_id)
        await self._store_inbound_message(message, conversation_id)

        response = await self._get_hermes_response(message, conversation_id)
        await self._store_outbound_message(message, conversation_id, response)

        if self._should_create_incident(response):
            incident = self._build_incident(message, conversation_id, response)
            created_incident = await self.incident_service.create_incident(incident)
            if response.incident is not None:
                response.incident.id = created_incident.id
                response.incident.conversation_id = created_incident.conversation_id
                response.incident.status = created_incident.status

        return response

    def build_conversation_id(self, message: IncomingMessage) -> str:
        return f"{message.channel}:{message.external_user_id}"

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
    ) -> AgentResponse:
        try:
            raw_response = await self.hermes_service.process_message(message, conversation_id)
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
    ) -> None:
        await self.firestore_service.create_document(
            "messages",
            {
                "conversation_id": conversation_id,
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
        response: AgentResponse,
    ) -> None:
        await self.firestore_service.create_document(
            "messages",
            {
                "conversation_id": conversation_id,
                "direction": "outbound",
                "channel": message.channel,
                "text": response.reply,
                "attachments": [],
                "metadata": {},
            },
        )
