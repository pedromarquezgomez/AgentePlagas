from typing import Any

import logging
from secrets import compare_digest

from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import PlainTextResponse

from app.adapters.whatsapp_adapter import WhatsAppAdapter, WhatsAppAdapterError
from app.config.settings import settings
from app.schemas.outgoing_message import OutgoingMessage
from app.services.conversation_service import ConversationService

router = APIRouter(tags=["whatsapp"])
whatsapp_adapter = WhatsAppAdapter(settings)
conversation_service = ConversationService()
logger = logging.getLogger(__name__)


@router.get("/webhooks/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    if hub_mode == "subscribe" and settings.whatsapp_verify_token and hub_challenge:
        if compare_digest(hub_verify_token or "", settings.whatsapp_verify_token):
            return PlainTextResponse(hub_challenge)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid WhatsApp verification token.",
    )


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(
    raw_update: dict[str, Any],
    x_whatsapp_webhook_secret: str | None = Header(default=None),
) -> dict[str, str]:
    if not settings.whatsapp_enabled:
        return {"status": "disabled"}

    _validate_whatsapp_secret(x_whatsapp_webhook_secret)
    logger.info("WhatsApp webhook received")

    try:
        incoming_message = whatsapp_adapter.parse_incoming(raw_update)
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
        await whatsapp_adapter.send_message(outgoing_message)
        logger.info(
            "WhatsApp response sent channel=%s external_user_id=%s conversation_id=%s",
            incoming_message.channel,
            incoming_message.external_user_id,
            conversation_id,
        )
    except WhatsAppAdapterError as exc:
        logger.warning("WhatsApp webhook failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {"status": "ok"}


def _validate_whatsapp_secret(received_secret: str | None) -> None:
    if not settings.whatsapp_webhook_secret:
        return

    if not received_secret or not compare_digest(
        received_secret,
        settings.whatsapp_webhook_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid WhatsApp webhook secret token.",
        )
