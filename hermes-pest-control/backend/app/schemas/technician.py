from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Technician(BaseModel):
    id: str | None = None
    name: str
    phone: str | None = None
    email: str | None = None
    active: bool = True
    service_area: str | None = None
    skills: list[str] = Field(default_factory=list)
    created_at: Any | None = None
    updated_at: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TechnicianCreate(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    active: bool = True
    service_area: str | None = None
    skills: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TechnicianUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    phone: str | None = None
    email: str | None = None
    active: bool | None = None
    service_area: str | None = None
    skills: list[str] | None = None
