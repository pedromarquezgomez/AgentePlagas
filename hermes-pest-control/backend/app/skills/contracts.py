from typing import Literal

from pydantic import BaseModel, Field


SkillRiskLevel = Literal["low", "medium", "high"]


class ProductSkill(BaseModel):
    name: str
    description: str
    allowed_outputs: list[str] = Field(default_factory=list)
    forbidden_effects: list[str] = Field(default_factory=list)
    risk_level: SkillRiskLevel = "low"
    requires_backend_service: bool = True
    instructions: str

    def as_prompt_section(self) -> str:
        allowed = ", ".join(self.allowed_outputs) or "none"
        forbidden = ", ".join(self.forbidden_effects) or "none"
        return "\n".join(
            [
                f"## {self.name}",
                self.description,
                f"Allowed outputs: {allowed}.",
                f"Forbidden effects: {forbidden}.",
                f"Risk level: {self.risk_level}.",
                f"Requires backend service: {self.requires_backend_service}.",
                self.instructions,
            ]
        )
