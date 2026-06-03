from unittest.mock import AsyncMock, MagicMock
import pytest

from app.context.manager import ContextManager
from app.policies.contracts import PolicyDecision
from app.schemas.incoming_message import IncomingMessage


def _incoming_message() -> IncomingMessage:
    return IncomingMessage(
        channel="telegram",
        external_user_id="test-user-1",
        external_chat_id="test-chat-1",
        message_type="text",
        text="Hola",
        attachments=[],
        metadata={},
    )


@pytest.mark.asyncio
async def test_context_manager_builds_complete_context() -> None:
    # Mocks
    mock_firestore = AsyncMock()
    mock_firestore.list_documents.return_value = []
    
    mock_skill_registry = MagicMock()
    mock_skill_registry.list_skills.return_value = []
    
    mock_tool_registry = MagicMock()
    mock_tool_registry.list_tools.return_value = []
    
    mock_policy_engine = MagicMock()
    mock_policy_engine.rules = {
        "test_tool": PolicyDecision.ALLOW,
        "secure_tool": PolicyDecision.REQUIRE_HUMAN_REVIEW,
    }

    manager = ContextManager(
        firestore_service=mock_firestore,
        skill_registry=mock_skill_registry,
        tool_registry=mock_tool_registry,
        policy_engine=mock_policy_engine,
    )

    context = await manager.build_context(
        incoming_message=_incoming_message(),
        conversation_history=[{"role": "user", "content": "Prev"}],
        business_context={"some_meta": "value"},
    )

    assert context.channel == "telegram"
    assert context.user_id == "test-user-1"
    assert context.conversation_id == "telegram:test-user-1"
    assert context.history == [{"role": "user", "content": "Prev"}]
    assert context.policy_constraints == {
        "test_tool": "ALLOW",
        "secure_tool": "REQUIRE_HUMAN_REVIEW",
    }
    assert context.metadata == {"some_meta": "value"}
    assert context.incident_id is None
    assert context.incident_summary is None
