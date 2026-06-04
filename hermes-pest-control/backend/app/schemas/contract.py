from typing import Any
from pydantic import BaseModel, ConfigDict


class Contract(BaseModel):
    id: str | None = None
    customer_id: str
    title: str
    pest_type: str
    frequency: str  # weekly, monthly, quarterly, annually
    amount: float
    status: str = "active"  # active, inactive
    start_date: str | None = None
    end_date: str | None = None
    next_visit_due: str | None = None
    created_at: Any | None = None
    updated_at: Any | None = None


class ContractCreate(BaseModel):
    customer_id: str
    title: str
    pest_type: str
    frequency: str
    amount: float
    status: str = "active"
    start_date: str | None = None
    end_date: str | None = None
    next_visit_due: str | None = None


class ContractUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    pest_type: str | None = None
    frequency: str | None = None
    amount: float | None = None
    status: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    next_visit_due: str | None = None
