import httpx

from app.config.settings import Settings
from app.context.contracts import ConversationContext
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

    async def process(self, context: ConversationContext) -> AgentResponse:
        business_context = {
            **context.metadata,
            "channel": context.channel,
            "user_id": context.user_id,
            "conversation_id": context.conversation_id,
            "incident_id": context.incident_id,
            "incident_summary": context.incident_summary,
            "policy_constraints": context.policy_constraints,
            "available_skills": [
                skill.model_dump(mode="json") for skill in context.available_skills
            ],
            "available_tools": [
                tool.as_runtime_metadata() for tool in context.available_tools
            ],
        }
        return await self.client.process_message(
            context.message,
            conversation_history=context.history,
            business_context=business_context,
        )

