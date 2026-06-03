from unittest.mock import AsyncMock, MagicMock
import pytest

from app.context.builders.history_builder import HistoryBuilder
from app.context.builders.incident_builder import IncidentBuilder
from app.context.builders.skills_builder import SkillsBuilder
from app.context.builders.tools_builder import ToolsBuilder
from app.skills.contracts import ProductSkill
from app.tools.contracts import BackendTool


@pytest.mark.asyncio
async def test_history_builder_uses_explicit_history() -> None:
    explicit_history = [{"role": "user", "content": "Hola"}]
    builder = HistoryBuilder(firestore_service=None)
    result = await builder.build("test-conv-id", conversation_history=explicit_history)
    assert result == explicit_history


@pytest.mark.asyncio
async def test_history_builder_loads_from_firestore() -> None:
    mock_firestore = AsyncMock()
    mock_firestore.list_documents.return_value = [
        {"direction": "inbound", "text": "Hola", "created_at": "2026-06-03T10:00:00Z"},
        {"direction": "outbound", "text": "¿En qué ayudo?", "created_at": "2026-06-03T10:00:01Z"},
    ]
    builder = HistoryBuilder(firestore_service=mock_firestore)
    result = await builder.build("test-conv-id")
    assert len(result) == 2
    assert result[0] == {"role": "user", "content": "Hola"}
    assert result[1] == {"role": "assistant", "content": "¿En qué ayudo?"}
    mock_firestore.list_documents.assert_called_once_with(
        "messages",
        filters={"conversation_id": "test-conv-id"},
    )


@pytest.mark.asyncio
async def test_history_builder_returns_empty_on_error() -> None:
    mock_firestore = AsyncMock()
    mock_firestore.list_documents.side_effect = RuntimeError("db error")
    builder = HistoryBuilder(firestore_service=mock_firestore)
    result = await builder.build("test-conv-id")
    assert result == []


@pytest.mark.asyncio
async def test_incident_builder_finds_active_incident() -> None:
    mock_firestore = AsyncMock()
    mock_firestore.list_documents.return_value = [
        {"id": "inc-1", "summary": "Cucarachas", "status": "pending_review", "created_at": "2026-06-03T10:00:00Z"},
        {"id": "inc-2", "summary": "Hormigas", "status": "closed", "created_at": "2026-06-03T10:01:00Z"},
    ]
    builder = IncidentBuilder(firestore_service=mock_firestore)
    inc_id, summary = await builder.build("test-conv-id")
    assert inc_id == "inc-1"
    assert summary == "Cucarachas"


@pytest.mark.asyncio
async def test_incident_builder_fallback_to_business_context() -> None:
    mock_firestore = AsyncMock()
    mock_firestore.list_documents.return_value = []
    builder = IncidentBuilder(firestore_service=mock_firestore)
    inc_id, summary = await builder.build(
        "test-conv-id",
        business_context={"incident_id": "inc-fallback", "incident_summary": "Fallback summary"},
    )
    assert inc_id == "inc-fallback"
    assert summary == "Fallback summary"


def test_skills_builder_loads_skills() -> None:
    mock_skill = MagicMock(spec=ProductSkill)
    mock_registry = MagicMock()
    mock_registry.list_skills.return_value = [mock_skill]
    builder = SkillsBuilder(skill_registry=mock_registry)
    result = builder.build()
    assert result == [mock_skill]


def test_tools_builder_loads_tools() -> None:
    mock_tool = MagicMock(spec=BackendTool)
    mock_registry = MagicMock()
    mock_registry.list_tools.return_value = [mock_tool]
    builder = ToolsBuilder(tool_registry=mock_registry)
    result = builder.build()
    assert result == [mock_tool]
