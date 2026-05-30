from typing import Any

from app.adapters.base_channel_adapter import BaseChannelAdapter
from app.schemas.incoming_message import IncomingMessage
from app.schemas.outgoing_message import OutgoingMessage


class WhatsAppAdapter(BaseChannelAdapter):
    def parse_incoming(self, raw_payload: dict[str, Any]) -> IncomingMessage:
        raise NotImplementedError("WhatsApp adapter is not implemented in this sprint.")

    async def send_message(self, outgoing_message: OutgoingMessage) -> dict[str, Any]:
        raise NotImplementedError("WhatsApp adapter is not implemented in this sprint.")

