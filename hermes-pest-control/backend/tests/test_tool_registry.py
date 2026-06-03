from app.tools.registry import ToolRegistry, default_tool_registry


def test_default_tool_registry_contains_initial_backend_tools() -> None:
    registry = default_tool_registry()

    names = {tool.name for tool in registry.list_tools()}

    assert names == {
        "create_incident_tool",
        "get_incident_tool",
        "list_incidents_tool",
        "escalate_to_human_tool",
        "suggest_visit_tool",
    }


def test_tool_registry_allows_known_tool_action() -> None:
    registry = default_tool_registry()

    assert registry.is_allowed("create_incident_tool", "create_incident") is True
    assert registry.is_allowed("get_incident_tool", "get_incident") is True


def test_tool_registry_denies_unknown_or_wrong_action() -> None:
    registry = default_tool_registry()

    assert registry.is_allowed("create_incident_tool", "delete_incident") is False
    assert registry.is_allowed("unknown_tool", "create_incident") is False


def test_tool_registry_marks_providers_and_skills_as_forbidden_callers() -> None:
    registry = default_tool_registry()

    for tool in registry.list_tools():
        assert "provider" in tool.forbidden_callers
        assert "skill" in tool.forbidden_callers
        assert tool.service_owner.endswith("Service")


def test_tool_registry_runtime_metadata_is_safe_for_providers() -> None:
    metadata = default_tool_registry().runtime_metadata()

    assert metadata[0]["name"] == "create_incident_tool"
    assert "service_owner" in metadata[0]
    assert "credentials" not in metadata[0]
    assert "secret" not in str(metadata).casefold()
