from app.schemas.agent_response import AgentResponse
from app.schemas.incoming_message import IncomingMessage


class EscalationService:
    async def should_escalate(
        self,
        message: IncomingMessage,
        response: AgentResponse,
    ) -> bool:
        return response.action.type == "escalate_to_human"
