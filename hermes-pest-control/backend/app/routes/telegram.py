from typing import Any

from secrets import compare_digest

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, HttpUrl

from app.adapters.telegram_adapter import TelegramAdapter, TelegramAdapterError
from app.config.settings import settings
from app.schemas.outgoing_message import OutgoingMessage
from app.services.conversation_service import ConversationService

router = APIRouter(tags=["telegram"])
telegram_adapter = TelegramAdapter(settings)
conversation_service = ConversationService()


class SetWebhookRequest(BaseModel):
    webhook_url: HttpUrl


@router.post("/webhooks/telegram")
async def telegram_webhook(
    raw_update: dict[str, Any],
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, str]:
    _validate_telegram_secret(x_telegram_bot_api_secret_token)

    try:
        incoming_message = telegram_adapter.parse_incoming(raw_update)
        agent_response = await conversation_service.handle_incoming_message(incoming_message)
        outgoing_message = OutgoingMessage(
            channel=incoming_message.channel,
            external_chat_id=incoming_message.external_chat_id,
            text=agent_response.reply,
            attachments=[],
            metadata={},
        )
        await telegram_adapter.send_message(outgoing_message)
    except TelegramAdapterError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {"status": "ok"}


@router.post("/telegram/set-webhook")
async def set_telegram_webhook(request: SetWebhookRequest) -> dict[str, Any]:
    try:
        return await telegram_adapter.set_webhook(str(request.webhook_url))
    except TelegramAdapterError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/telegram/webhook-info")
async def get_telegram_webhook_info() -> dict[str, Any]:
    try:
        return await telegram_adapter.get_webhook_info()
    except TelegramAdapterError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


def _validate_telegram_secret(received_secret: str | None) -> None:
    if not settings.telegram_webhook_secret:
        return

    if not received_secret or not compare_digest(
        received_secret,
        settings.telegram_webhook_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram webhook secret token.",
        )
