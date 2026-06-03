from typing import Any

from app.config.settings import Settings
from app.context.contracts import ConversationContext
from app.context.builders.history_builder import HistoryBuilder
from app.context.builders.incident_builder import IncidentBuilder
from app.context.builders.skills_builder import SkillsBuilder
from app.context.builders.tools_builder import ToolsBuilder
from app.policies.engine import PolicyEngine
from app.schemas.incoming_message import IncomingMessage
from app.services.firestore_factory import get_firestore_service
from app.skills.registry import default_skill_registry
from app.tools.registry import default_tool_registry


class ContextManager:
    def __init__(
        self,
        firestore_service: Any = None,
        skill_registry: Any = None,
        tool_registry: Any = None,
        policy_engine: Any = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.firestore_service = firestore_service or get_firestore_service()
        self.skill_registry = skill_registry or default_skill_registry()
        self.tool_registry = tool_registry or default_tool_registry()
        self.policy_engine = policy_engine or PolicyEngine()

        self.history_builder = HistoryBuilder(self.firestore_service)
        self.incident_builder = IncidentBuilder(self.firestore_service)
        self.skills_builder = SkillsBuilder(self.skill_registry)
        self.tools_builder = ToolsBuilder(self.tool_registry)

    async def build_context(
        self,
        incoming_message: IncomingMessage,
        conversation_history: list[dict[str, Any]] | None = None,
        business_context: dict[str, Any] | None = None,
    ) -> ConversationContext:
        channel = incoming_message.channel
        user_id = incoming_message.external_user_id
        conversation_id = f"{channel}:{user_id}"

        # Ejecutar los builders
        history = await self.history_builder.build(
            conversation_id,
            conversation_history,
        )
        incident_id, incident_summary = await self.incident_builder.build(
            conversation_id,
            business_context,
        )
        skills = self.skills_builder.build()
        tools = self.tools_builder.build()

        # Extraer restricciones de políticas
        policy_constraints = {}
        if self.policy_engine and hasattr(self.policy_engine, "get_constraints"):
            policy_constraints = self.policy_engine.get_constraints()


        # Combinar metadatos a partir de business_context
        metadata = {}
        if business_context:
            metadata.update(business_context)

        return ConversationContext(
            message=incoming_message,
            channel=channel,
            user_id=user_id,
            conversation_id=conversation_id,
            incident_id=incident_id,
            incident_summary=incident_summary,
            history=history,
            available_skills=skills,
            available_tools=tools,
            policy_constraints=policy_constraints,
            metadata=metadata,
        )
