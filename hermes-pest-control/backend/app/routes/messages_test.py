from fastapi import APIRouter, HTTPException, status

from app.config.settings import settings
from app.schemas.agent_response import AgentResponse
from app.schemas.incoming_message import IncomingMessage
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/messages", tags=["messages"])
conversation_service = ConversationService()
__test__ = False


@router.post("/test", response_model=AgentResponse)
async def test_message(message: IncomingMessage) -> AgentResponse:
    if settings.app_env == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Development message test endpoint is disabled in production.",
        )

    return await conversation_service.handle_incoming_message(message)
