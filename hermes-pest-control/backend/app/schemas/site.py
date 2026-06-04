from typing import Any
from pydantic import BaseModel, ConfigDict


class Site(BaseModel):
    id: str | None = None
    customer_id: str
    name: str
    address: str
    latitude: float | None = None
    longitude: float | None = None
    created_at: Any | None = None
    updated_at: Any | None = None


class SiteCreate(BaseModel):
    customer_id: str
    name: str
    address: str
    latitude: float | None = None
    longitude: float | None = None


class SiteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
