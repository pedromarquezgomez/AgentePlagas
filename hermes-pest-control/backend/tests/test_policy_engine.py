from app.policies.contracts import PolicyContext, PolicyDecision
from app.policies.engine import PolicyEngine


def test_allow_policy() -> None:
    decision = PolicyEngine().evaluate(
        PolicyContext(
            channel="telegram",
            user_id="user-1",
            incident_id=None,
            requested_tool="create_incident_tool",
            requested_action="create_incident",
            source_provider="llm",
            confidence=0.9,
        )
    )

    assert decision.decision == PolicyDecision.ALLOW
    assert decision.policy_rule == "default.create_incident_tool"


def test_deny_policy() -> None:
    decision = PolicyEngine().evaluate(
        PolicyContext(
            channel="telegram",
            user_id="user-1",
            requested_tool="firestore.direct_write",
            requested_action="write",
            source_provider="llm",
        )
    )

    assert decision.decision == PolicyDecision.DENY
    assert decision.policy_rule == "default.deny_unknown_tool"


def test_human_review_policy() -> None:
    decision = PolicyEngine().evaluate(
        PolicyContext(
            channel="telegram",
            user_id="user-1",
            incident_id="incident-1",
            requested_tool="suggest_visit_tool",
            requested_action="suggest_visit",
            source_provider="llm",
            confidence=0.7,
        )
    )

    assert decision.decision == PolicyDecision.REQUIRE_HUMAN_REVIEW
    assert decision.policy_rule == "default.suggest_visit_tool"
