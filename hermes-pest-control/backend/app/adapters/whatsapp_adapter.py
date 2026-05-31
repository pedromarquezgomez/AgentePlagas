from typing import Any

import httpx

from app.adapters.base_channel_adapter import BaseChannelAdapter
from app.config.settings import Settings
from app.schemas.incoming_message import IncomingMessage
from app.schemas.outgoing_message import OutgoingMessage


class WhatsAppAdapterError(RuntimeError):
    pass


class WhatsAppAdapter(BaseChannelAdapter):
    channel = "whatsapp"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def parse_incoming(self, raw_payload: dict[str, Any]) -> IncomingMessage:
        value = self._extract_value(raw_payload)
        messages = value.get("messages") or []
        if not messages:
            raise WhatsAppAdapterError("WhatsApp payload does not contain a supported message.")

        message = messages[0]
        sender_id = message.get("from")
        message_id = message.get("id")
        if not sender_id or not message_id:
            raise WhatsAppAdapterError("WhatsApp message is missing sender id or message id.")

        contacts = value.get("contacts") or []
        contact = contacts[0] if contacts else {}
        metadata = value.get("metadata") or {}
        phone_number_id = metadata.get("phone_number_id")
        message_type = message.get("type", "unknown")
        text = self._parse_text(message, message_type)
        attachments = self._parse_attachments(message, message_type)

        return IncomingMessage(
            channel=self.channel,
            external_user_id=str(sender_id),
            external_chat_id=str(sender_id),
            message_type=self._normalized_message_type(message_type, text, attachments),
            text=text,
            attachments=attachments,
            metadata={
                "whatsapp_message_id": message_id,
                "whatsapp_timestamp": message.get("timestamp"),
                "whatsapp_type": message_type,
                "contact_id": contact.get("wa_id"),
                "contact_name": (contact.get("profile") or {}).get("name"),
                "phone_number_id": phone_number_id,
                "display_phone_number": metadata.get("display_phone_number"),
            },
        )

    async def send_message(self, outgoing_message: OutgoingMessage) -> dict[str, Any]:
        if not self.settings.whatsapp_enabled:
            raise WhatsAppAdapterError("WhatsApp integration is disabled.")
        if self.settings.whatsapp_provider == "mock":
            return {
                "mock": True,
                "messages": [{"id": "mock-whatsapp-message"}],
                "to": outgoing_message.external_chat_id,
            }
        if not self.settings.whatsapp_access_token:
            raise WhatsAppAdapterError("WHATSAPP_ACCESS_TOKEN is not configured.")
        if not self.settings.whatsapp_phone_number_id:
            raise WhatsAppAdapterError("WHATSAPP_PHONE_NUMBER_ID is not configured.")

        url = (
            f"https://graph.facebook.com/{self.settings.whatsapp_graph_api_version}/"
            f"{self.settings.whatsapp_phone_number_id}/messages"
        )
        payload = {
            "messaging_product": "whatsapp",
            "to": outgoing_message.external_chat_id,
            "type": "text",
            "text": {"body": outgoing_message.text},
        }
        headers = {"Authorization": f"Bearer {self.settings.whatsapp_access_token}"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise WhatsAppAdapterError("WhatsApp sendMessage request failed.") from exc

        return self._parse_whatsapp_response(response)

    def _extract_value(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return raw_payload["entry"][0]["changes"][0]["value"]
        except (KeyError, IndexError, TypeError) as exc:
            raise WhatsAppAdapterError("WhatsApp payload has an invalid structure.") from exc

    def _parse_text(self, message: dict[str, Any], message_type: str) -> str | None:
        if message_type == "text":
            return (message.get("text") or {}).get("body")
        if message_type in {"image", "document", "audio", "video"}:
            return (message.get(message_type) or {}).get("caption")
        return None

    def _parse_attachments(
        self,
        message: dict[str, Any],
        message_type: str,
    ) -> list[dict[str, Any]]:
        if message_type not in {"image", "document", "audio", "video"}:
            return []

        attachment = message.get(message_type) or {}
        return [
            {
                "type": message_type,
                "id": attachment.get("id"),
                "mime_type": attachment.get("mime_type"),
                "sha256": attachment.get("sha256"),
                "filename": attachment.get("filename"),
                "caption": attachment.get("caption"),
            }
        ]

    def _normalized_message_type(
        self,
        whatsapp_type: str,
        text: str | None,
        attachments: list[dict[str, Any]],
    ) -> str:
        if text:
            return "text"
        if attachments:
            return "image" if whatsapp_type == "image" else "file"
        return "unknown"

    def _parse_whatsapp_response(self, response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise WhatsAppAdapterError("WhatsApp API returned invalid JSON.") from exc

        if response.status_code >= 400 or data.get("error"):
            error = data.get("error") or {}
            message = error.get("message", "unknown WhatsApp API error")
            raise WhatsAppAdapterError(f"WhatsApp sendMessage failed: {message}")

        return data
