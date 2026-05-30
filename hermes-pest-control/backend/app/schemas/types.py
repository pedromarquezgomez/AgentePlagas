from typing import Literal

Channel = Literal["telegram", "whatsapp", "webchat", "email", "sms"]
MessageType = Literal["text", "image", "file", "unknown"]
AgentActionType = Literal["create_incident", "collect_missing_data", "escalate_to_human"]
IncidentPriority = Literal["low", "medium", "high", "urgent"]
IncidentStatus = Literal[
    "pending_review",
    "triaged",
    "scheduled",
    "assigned",
    "in_progress",
    "resolved",
    "cancelled",
]

