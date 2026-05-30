from typing import Any

from app.adapters.base_channel_adapter import BaseChannelAdapter
from app.schemas.incoming_message import IncomingMessage
from app.schemas.outgoing_message import OutgoingMessage


class TelegramAdapter(BaseChannelAdapter):
    channel = "telegram"

    def parse_incoming(self, raw_payload: dict[str, Any]) -> IncomingMessage:
        message = raw_payload.get("message") or raw_payload.get("edited_message") or {}
        user = message.get("from") or {}
        chat = message.get("chat") or {}

        return IncomingMessage(
            channel=self.channel,
            external_user_id=str(user.get("id", "")),
            external_chat_id=str(chat.get("id", "")),
            message_type="text" if message.get("text") else "unknown",
            text=message.get("text"),
            attachments=[],
            metadata={"raw_update_id": raw_payload.get("update_id")},
        )

    async def send_message(self, outgoing_message: OutgoingMessage) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "provider": "telegram_bot_api",
            "status": "not_sent_mock",
            "payload": {
                "chat_id": outgoing_message.external_chat_id,
                "text": outgoing_message.text,
            },
        }

