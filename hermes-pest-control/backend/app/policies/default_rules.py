from app.policies.contracts import PolicyDecision


DEFAULT_TOOL_POLICY_RULES: dict[str, PolicyDecision] = {
    "create_incident_tool": PolicyDecision.ALLOW,
    "get_incident_tool": PolicyDecision.ALLOW,
    "list_incidents_tool": PolicyDecision.ALLOW,
    "suggest_visit_tool": PolicyDecision.REQUIRE_HUMAN_REVIEW,
    "escalate_to_human_tool": PolicyDecision.ALLOW,
    # Controlled Gmail draft execution requires approval.
    "gmail.create_draft": PolicyDecision.REQUIRE_HUMAN_REVIEW,
    "gmail.send_email": PolicyDecision.DENY,
    "schedule_visit_tool": PolicyDecision.REQUIRE_HUMAN_REVIEW,
}
