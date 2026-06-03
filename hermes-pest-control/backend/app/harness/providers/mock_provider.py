from app.harness.contracts import AgentRuntimeRequest
from app.schemas.agent_response import AgentResponse
from app.services.hermes_clients import HermesMockClient


class MockAgentRuntimeProvider:
    name = "mock_provider"
    mode = "mock"

    def __init__(self, client: HermesMockClient | None = None) -> None:
        self.client = client or HermesMockClient()

    async def process(self, request: AgentRuntimeRequest) -> AgentResponse:
        return await self.client.process_message(
            request.incoming_message,
            conversation_history=request.conversation_history,
            business_context=request.business_context,
        )
