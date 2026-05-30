from typing import Any

import httpx

from app.adapters.base_channel_adapter import BaseChannelAdapter
from app.config.settings import Settings
from app.schemas.incoming_message import IncomingMessage
from app.schemas.outgoing_message import OutgoingMessage


class TelegramAdapterError(RuntimeError):
    pass


class TelegramAdapter(BaseChannelAdapter):
    channel = "telegram"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def parse_incoming(self, raw_payload: dict[str, Any]) -> IncomingMessage:
        message = raw_payload.get("message") or raw_payload.get("edited_message") or {}
        if not message:
            raise TelegramAdapterError("Telegram payload does not contain a supported message.")

        user = message.get("from") or {}
        chat = message.get("chat") or {}
        user_id = user.get("id")
        chat_id = chat.get("id")
        if user_id is None or chat_id is None:
            raise TelegramAdapterError("Telegram message is missing user id or chat id.")

        photos = message.get("photo") or []
        text = message.get("text") or message.get("caption")

        return IncomingMessage(
            channel=self.channel,
            external_user_id=str(user_id),
            external_chat_id=str(chat_id),
            message_type=self._message_type(text, photos),
            text=text,
            attachments=self._parse_photo_attachments(photos),
            metadata={
                "raw_update_id": raw_payload.get("update_id"),
                "message_id": message.get("message_id"),
                "telegram_date": message.get("date"),
                "username": user.get("username"),
                "first_name": user.get("first_name"),
                "chat_type": chat.get("type"),
            },
        )

    async def send_message(self, outgoing_message: OutgoingMessage) -> dict[str, Any]:
        return await self._post_to_telegram(
            "sendMessage",
            {
                "chat_id": outgoing_message.external_chat_id,
                "text": outgoing_message.text,
            },
        )

    async def set_webhook(self, webhook_url: str) -> dict[str, Any]:
        payload: dict[str, Any] = {"url": webhook_url}
        if self.settings.telegram_webhook_secret:
            payload["secret_token"] = self.settings.telegram_webhook_secret
        return await self._post_to_telegram("setWebhook", payload)

    async def get_webhook_info(self) -> dict[str, Any]:
        return await self._get_from_telegram("getWebhookInfo")

    def _message_type(self, text: str | None, photos: list[dict[str, Any]]) -> str:
        if text:
            return "text"
        if photos:
            return "image"
        return "unknown"

    def _parse_photo_attachments(self, photos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        attachments = []
        for photo in photos:
            attachments.append(
                {
                    "type": "photo",
                    "file_id": photo.get("file_id"),
                    "file_unique_id": photo.get("file_unique_id"),
                    "width": photo.get("width"),
                    "height": photo.get("height"),
                    "file_size": photo.get("file_size"),
                }
            )
        return attachments

    async def _post_to_telegram(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        token = self._require_token()
        url = f"https://api.telegram.org/bot{token}/{method}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise TelegramAdapterError(f"Telegram {method} request failed.") from exc

        return self._parse_telegram_response(method, response)

    async def _get_from_telegram(self, method: str) -> dict[str, Any]:
        token = self._require_token()
        url = f"https://api.telegram.org/bot{token}/{method}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
        except httpx.HTTPError as exc:
            raise TelegramAdapterError(f"Telegram {method} request failed.") from exc

        return self._parse_telegram_response(method, response)

    def _parse_telegram_response(self, method: str, response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise TelegramAdapterError(f"Telegram {method} returned invalid JSON.") from exc

        if response.status_code >= 400 or data.get("ok") is not True:
            description = data.get("description", "unknown Telegram API error")
            raise TelegramAdapterError(f"Telegram {method} failed: {description}")

        return data

    def _require_token(self) -> str:
        if not self.settings.telegram_bot_token:
            raise TelegramAdapterError("TELEGRAM_BOT_TOKEN is not configured.")
        return self.settings.telegram_bot_token
