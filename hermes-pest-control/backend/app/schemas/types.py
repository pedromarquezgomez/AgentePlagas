from typing import Literal

Channel = Literal["telegram", "whatsapp", "webchat", "email", "sms"]
MessageType = Literal["text", "image", "file", "unknown"]
AgentActionType = Literal[
    "reply_only",
    "create_incident",
    "collect_missing_data",
    "escalate_to_human",
    "schedule_visit_selection",
    "technical_diagnosis",
    "out_of_domain",
]
IncidentPriority = Literal["low", "medium", "high", "urgent"]
HumanReviewStatus = Literal["open", "in_review", "resolved", "dismissed"]
HumanReviewReason = Literal[
    "fallback_used",
    "agent_escalation",
    "urgent_priority",
    "sensitive_case",
]
VisitStatus = Literal["draft", "scheduled", "in_progress", "completed", "cancelled"]
OperationalDocumentType = Literal[
    "incident_summary",
    "technician_brief",
    "post_treatment_recommendations",
    "work_report_draft",
]
OperationalDocumentStatus = Literal["draft", "reviewed", "archived"]
OperationalDocumentGeneratedBy = Literal["system", "admin", "agent_proposal"]
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
