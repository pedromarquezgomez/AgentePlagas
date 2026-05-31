from typing import Literal

Channel = Literal["telegram", "whatsapp", "webchat", "email", "sms"]
MessageType = Literal["text", "image", "file", "unknown"]
AgentActionType = Literal["create_incident", "collect_missing_data", "escalate_to_human"]
IncidentPriority = Literal["low", "medium", "high", "urgent"]
HumanReviewStatus = Literal["open", "in_review", "resolved", "dismissed"]
HumanReviewReason = Literal[
    "fallback_used",
    "agent_escalation",
    "urgent_priority",
    "sensitive_case",
]
VisitStatus = Literal["draft", "scheduled", "in_progress", "completed", "cancelled"]
IncidentStatus = Literal[
    "new",
    "pending_review",
    "waiting_for_client_data",
    "ready_for_scheduling",
    "scheduled",
    "in_progress",
    "completed",
    "follow_up_pending",
    "closed",
    "cancelled",
]
