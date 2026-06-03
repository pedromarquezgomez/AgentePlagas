from app.context.contracts import ConversationContext
from app.schemas.agent_response import AgentResponse
from app.services.hermes_clients import HermesMockClient


class MockAgentRuntimeProvider:
    name = "mock_provider"
    mode = "mock"

    def __init__(self, client: HermesMockClient | None = None) -> None:
        self.client = client or HermesMockClient()

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

