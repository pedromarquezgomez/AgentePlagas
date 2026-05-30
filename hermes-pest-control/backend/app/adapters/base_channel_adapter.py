from abc import ABC, abstractmethod
from typing import Any

from app.schemas.incoming_message import IncomingMessage
from app.schemas.outgoing_message import OutgoingMessage


class BaseChannelAdapter(ABC):
    @abstractmethod
    def parse_incoming(self, raw_payload: dict[str, Any]) -> IncomingMessage:
        """Normalize a channel-specific payload into the internal message contract."""

    @abstractmethod
    async def send_message(self, outgoing_message: OutgoingMessage) -> dict[str, Any]:
        """Send a normalized outgoing message through the channel provider."""

