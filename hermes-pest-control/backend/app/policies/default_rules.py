from app.policies.contracts import PolicyDecision


DEFAULT_TOOL_POLICY_RULES: dict[str, PolicyDecision] = {
    "create_incident_tool": PolicyDecision.ALLOW,
    "get_incident_tool": PolicyDecision.ALLOW,
    "list_incidents_tool": PolicyDecision.ALLOW,
    "suggest_visit_tool": PolicyDecision.REQUIRE_HUMAN_REVIEW,
    "escalate_to_human_tool": PolicyDecision.ALLOW,
    # Compatibility for Sprint 25 controlled Gmail draft execution. This is
    # still guarded by review_status=approved and Gmail feature flags.
    "gmail.create_draft": PolicyDecision.ALLOW,
}
