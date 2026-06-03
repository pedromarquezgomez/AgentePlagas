from app.policies.contracts import PolicyContext, PolicyDecision, PolicyEvaluation
from app.policies.default_rules import DEFAULT_TOOL_POLICY_RULES


class PolicyEngine:
    def __init__(
        self,
        rules: dict[str, PolicyDecision] | None = None,
    ) -> None:
        self.rules = rules or DEFAULT_TOOL_POLICY_RULES

    def evaluate(self, context: PolicyContext) -> PolicyEvaluation:
        decision = self.rules.get(context.requested_tool)
        if decision is None:
            return PolicyEvaluation(
                decision=PolicyDecision.DENY,
                policy_rule="default.deny_unknown_tool",
                reason=f"Tool is not allowed by policy: {context.requested_tool}",
            )

        return PolicyEvaluation(
            decision=decision,
            policy_rule=f"default.{context.requested_tool}",
            reason=self._reason_for(decision, context.requested_tool),
        )

    def _reason_for(self, decision: PolicyDecision, requested_tool: str) -> str:
        if decision == PolicyDecision.ALLOW:
            return f"Tool allowed by harness policy: {requested_tool}"
        if decision == PolicyDecision.REQUIRE_HUMAN_REVIEW:
            return f"Tool requires human review by harness policy: {requested_tool}"
        return f"Tool denied by harness policy: {requested_tool}"
