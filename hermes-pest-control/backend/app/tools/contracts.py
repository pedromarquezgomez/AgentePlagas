from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.tool_harness import ToolRiskLevel


ToolExecutionPolicy = Literal[
    "proposal_only",
    "backend_service_only",
    "review_required",
    "disabled",
]


class BackendTool(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    service_owner: str = Field(min_length=1)
    allowed_actions: list[str] = Field(default_factory=list)
    risk_level: ToolRiskLevel
    requires_approval: bool = True
    execution_policy: ToolExecutionPolicy = "backend_service_only"
    enabled: bool = True
    forbidden_callers: list[str] = Field(default_factory=lambda: ["provider", "skill"])
    notes: str = ""

    def is_action_allowed(self, action: str) -> bool:
        return self.enabled and action in self.allowed_actions

    def as_runtime_metadata(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "allowed_actions": list(self.allowed_actions),
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
            "execution_policy": self.execution_policy,
            "service_owner": self.service_owner,
        }
