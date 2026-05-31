from fastapi import APIRouter

from app.schemas.agent_response import AgentResponse
from app.schemas.incoming_message import IncomingMessage
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/messages", tags=["messages"])
conversation_service = ConversationService()
__test__ = False


@router.post("/test", response_model=AgentResponse)
async def test_message(message: IncomingMessage) -> AgentResponse:
    return await conversation_service.handle_incoming_message(message)
