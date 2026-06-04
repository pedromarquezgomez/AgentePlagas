from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from app.customers.contracts import CustomerType


class Customer(BaseModel):
    id: str | None = None
    name: str
    email: str | None = None
    phone: str | None = None
    telegram_user_id: str | None = None
    whatsapp_phone: str | None = None
    customer_type: CustomerType = CustomerType.UNKNOWN
    created_at: Any | None = None
    updated_at: Any | None = None


class CustomerCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    telegram_user_id: str | None = None
    whatsapp_phone: str | None = None
    customer_type: CustomerType = CustomerType.UNKNOWN


class CustomerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    telegram_user_id: str | None = None
    whatsapp_phone: str | None = None
    customer_type: CustomerType | None = None
