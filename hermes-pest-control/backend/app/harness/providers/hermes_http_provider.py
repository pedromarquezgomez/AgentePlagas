import httpx

from app.config.settings import Settings
from app.harness.contracts import AgentRuntimeRequest
from app.schemas.agent_response import AgentResponse
from app.services.hermes_clients import HermesRealClient


class HermesHttpRuntimeProvider:
    name = "hermes_http_provider"
    mode = "nous_hermes"

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        client: HermesRealClient | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.client = client or HermesRealClient(self.settings, transport=transport)

    async def process(self, request: AgentRuntimeRequest) -> AgentResponse:
        business_context = {
            **request.business_context,
            "available_skills": [
                skill.model_dump(mode="json") for skill in request.available_skills
            ],
        }
        return await self.client.process_message(
            request.incoming_message,
            conversation_history=request.conversation_history,
            business_context=business_context,
        )
