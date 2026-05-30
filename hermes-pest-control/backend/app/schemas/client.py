from pydantic import BaseModel


class Client(BaseModel):
    id: str | None = None
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    telegram_user_id: str | None = None
    whatsapp_phone: str | None = None
    default_location: str | None = None

