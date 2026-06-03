from app.skills.registry import SkillRegistry, default_skill_registry


def test_default_skill_registry_contains_initial_product_skills() -> None:
    registry = default_skill_registry()

    names = {skill.name for skill in registry.list_skills()}

    assert names == {
        "create_incident",
        "classify_pest",
        "request_missing_info",
        "escalate_to_human",
        "suggest_visit",
        "summarize_case",
    }


def test_skill_registry_skills_are_declarative_and_non_executing() -> None:
    registry = default_skill_registry()

    for skill in registry.list_skills():
        assert skill.requires_backend_service is True
        assert any(
            effect in skill.forbidden_effects
            for effect in [
                "database_write",
                "direct_firestore_write",
                "channel_send",
                "tool_execution",
                "calendar_write",
                "document_persist",
            ]
        )


def test_skill_registry_requires_known_skill() -> None:
    registry = SkillRegistry()

    skill = registry.require_skill("create_incident")

    assert skill.name == "create_incident"
    assert "AgentResponse" in skill.instructions or "backend" in skill.instructions


def test_skill_registry_prompt_sections_are_provider_neutral() -> None:
    sections = default_skill_registry().prompt_sections()

    combined = "\n".join(sections)
    assert "create_incident" in combined
    assert "Nous" not in combined
    assert "Hermes Agent" not in combined
