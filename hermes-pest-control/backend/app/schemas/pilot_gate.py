from typing import Literal

from pydantic import BaseModel, Field


PilotRoute = Literal["agent", "mock", "human_review"]


class PilotGateResult(BaseModel):
    eligible: bool
    reason: str
    risk_flags: list[str] = Field(default_factory=list)
    route: PilotRoute
    policy_rule: str
