from typing import Protocol, runtime_checkable

from app.harness.contracts import AgentRuntimeRequest
from app.schemas.agent_response import AgentResponse


@runtime_checkable
class AgentRuntimeProvider(Protocol):
    name: str
    mode: str

    async def process(self, request: AgentRuntimeRequest) -> AgentResponse:
        ...


class LegacyClientRuntimeProvider:
    """Compatibility adapter for older process_message clients used in tests."""

    def __init__(self, client, *, name: str = "legacy_client", mode: str = "unknown"):
        self.client = client
        self.name = name
        self.mode = mode

    async def process(self, request: AgentRuntimeRequest) -> AgentResponse:
        return await self.client.process_message(
            request.incoming_message,
            conversation_history=request.conversation_history,
            business_context=request.business_context,
        )
