from typing import Protocol, runtime_checkable

from app.context.contracts import ConversationContext
from app.schemas.agent_response import AgentResponse


@runtime_checkable
class AgentRuntimeProvider(Protocol):
    name: str
    mode: str

    async def process(self, context: ConversationContext) -> AgentResponse:
        ...


class LegacyClientRuntimeProvider:
    """Compatibility adapter for older process_message clients used in tests."""

    def __init__(self, client, *, name: str = "legacy_client", mode: str = "unknown"):
        self.client = client
        self.name = name
        self.mode = mode

    async def process(self, context: ConversationContext) -> AgentResponse:
        business_context = {
            **context.metadata,
            "channel": context.channel,
            "user_id": context.user_id,
            "conversation_id": context.conversation_id,
            "incident_id": context.incident_id,
            "incident_summary": context.incident_summary,
            "policy_constraints": context.policy_constraints,
        }
        return await self.client.process_message(
            context.message,
            conversation_history=context.history,
            business_context=business_context,
        )

