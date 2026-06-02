from app.config.settings import Settings
from app.schemas.tool_harness import ToolDecision, ToolExecutionRecord, ToolRequest


class HermesToolHarness:
    """Policy gate for experimental Nous Hermes tool proposals.

    This harness intentionally does not execute tools. It converts proposed
    external actions into auditable decisions for review or future controlled
    execution.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def decide(self, request: ToolRequest) -> ToolDecision:
        provider = request.provider.lower()
        action = request.action.lower()
        risk_level = int(request.risk_level)
        payload_text = str(request.payload).lower()

        if self.settings.tool_harness_enforcement != "strict":
            return ToolDecision(
                deny=True,
                reason="Only strict enforcement is supported in this PoC.",
                policy_rule="tool_harness.strict_only",
            )

        if not self.settings.nous_hermes_tools_enabled:
            return ToolDecision(
                deny=True,
                reason="Nous Hermes tool execution is disabled by feature flag.",
                policy_rule="nous_hermes.tools_disabled",
            )

        if not self._is_allowed_tool(request.tool_name):
            return ToolDecision(
                deny=True,
                reason="The proposed tool is not in NOUS_HERMES_ALLOWED_TOOLS.",
                policy_rule="tool_harness.allowed_tools",
            )

        if provider == "firestore":
            return ToolDecision(
                deny=True,
                reason="Direct Firestore access by Nous Hermes is not allowed.",
                policy_rule="firestore.direct_access_denied",
            )

        if provider in {"incident_service", "internal"}:
            if action in {"propose_incident", "create_incident"}:
                return ToolDecision(
                    allow=True,
                    reason=(
                        "Incident proposals are allowed as PoC output only; "
                        "no incident is written by the experimental adapter."
                    ),
                    policy_rule="incident.proposal_only",
                )
            return ToolDecision(
                deny=True,
                reason="The proposed internal action is not allowed in the PoC.",
                policy_rule="internal.action_not_allowed",
            )

        if provider == "gmail":
            if action in {"create_draft", "draft_email"}:
                return ToolDecision(
                    convert_to_draft=True,
                    reason="Gmail proposals are converted to drafts in the PoC.",
                    policy_rule="gmail.draft_only",
                )
            if action == "send_email":
                return ToolDecision(
                    deny=True,
                    reason="Direct email sending is not allowed in the PoC.",
                    policy_rule="gmail.send_denied_in_poc",
                )
            return ToolDecision(
                require_human_approval=True,
                reason="Sending email requires human approval.",
                policy_rule="gmail.send_requires_approval",
            )

        if provider == "calendar":
            if action in {"propose_event", "create_event"}:
                return ToolDecision(
                    require_human_approval=True,
                    reason="Calendar events are proposals until reviewed.",
                    policy_rule="calendar.event_requires_review",
                )
            return ToolDecision(
                deny=True,
                reason="The proposed calendar action is not allowed in the PoC.",
                policy_rule="calendar.action_not_allowed",
            )

        if provider in {"telegram", "whatsapp"}:
            if risk_level >= 5 or any(
                term in payload_text
                for term in ("producto químico", "producto quimico", "fumigue", "fumigar")
            ):
                return ToolDecision(
                    deny=True,
                    reason=(
                        "Dangerous chemical or fumigation advice cannot be sent "
                        "by an agent proposal."
                    ),
                    policy_rule="channels.dangerous_advice_denied",
                )
            return ToolDecision(
                require_human_approval=True,
                reason="Channel messages proposed by Nous Hermes require review.",
                policy_rule="channels.message_requires_review",
            )

        return ToolDecision(
            deny=True,
            reason="Provider is not approved for controlled Nous Hermes tools.",
            policy_rule="tool_harness.provider_not_allowed",
        )

    def build_execution_record(
        self,
        request: ToolRequest,
        decision: ToolDecision,
    ) -> ToolExecutionRecord:
        return ToolExecutionRecord(
            tool_request_id=request.id,
            tool_decision_id=decision.audit_id,
            trace_id=request.trace_id,
            conversation_id=request.conversation_id,
            tool_name=request.tool_name,
            provider=request.provider,
            action=request.action,
            risk_level=request.risk_level,
            requires_approval=request.requires_approval,
            decision=decision.outcome,
            execution_status=self._execution_status(decision),
            review_status="proposed",
            executed=False,
            external_effect=False,
            metadata={
                "poc": True,
                "external_tools_executed": False,
                "policy_rule": decision.policy_rule,
                "target": request.target,
                "payload": request.payload,
                "reason": request.reason,
            },
        )

    def _is_allowed_tool(self, tool_name: str) -> bool:
        allowed = {
            item.strip()
            for item in self.settings.nous_hermes_allowed_tools.split(",")
            if item.strip()
        }
        return bool(allowed) and tool_name in allowed

    def _execution_status(self, decision: ToolDecision) -> str:
        if decision.deny:
            return "blocked"
        if decision.convert_to_draft:
            return "draft_proposed"
        if decision.require_human_approval:
            return "pending_human_approval"
        if decision.require_more_data:
            return "requires_more_data"
        return "allowed_not_executed"
