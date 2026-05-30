from typing import Any

import logging
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
logger = logging.getLogger(__name__)


class SetWebhookRequest(BaseModel):
    webhook_url: HttpUrl


@router.post("/webhooks/telegram")
async def telegram_webhook(
    raw_update: dict[str, Any],
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, str]:
    _validate_telegram_secret(x_telegram_bot_api_secret_token)
    logger.info("Telegram webhook received update_id=%s", raw_update.get("update_id"))

    try:
        incoming_message = telegram_adapter.parse_incoming(raw_update)
        conversation_id = conversation_service.build_conversation_id(incoming_message)
        logger.info(
            "IncomingMessage normalized channel=%s external_user_id=%s "
            "conversation_id=%s message_type=%s attachment_count=%s",
            incoming_message.channel,
            incoming_message.external_user_id,
            conversation_id,
            incoming_message.message_type,
            len(incoming_message.attachments),
        )

        agent_response = await conversation_service.handle_incoming_message(incoming_message)
        incident_should_create = (
            agent_response.incident.should_create
            if agent_response.incident is not None
            else False
        )
        logger.info(
            "ConversationService completed channel=%s external_user_id=%s "
            "conversation_id=%s action_type=%s incident_should_create=%s",
            incoming_message.channel,
            incoming_message.external_user_id,
            conversation_id,
            agent_response.action.type,
            incident_should_create,
        )

        outgoing_message = OutgoingMessage(
            channel=incoming_message.channel,
            external_chat_id=incoming_message.external_chat_id,
            text=agent_response.reply,
            attachments=[],
            metadata={},
        )
        await telegram_adapter.send_message(outgoing_message)
        logger.info(
            "Telegram response sent channel=%s external_user_id=%s conversation_id=%s",
            incoming_message.channel,
            incoming_message.external_user_id,
            conversation_id,
        )
    except TelegramAdapterError as exc:
        logger.warning("Telegram webhook failed: %s", exc)
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
