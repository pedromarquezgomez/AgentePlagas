from typing import Any
from pydantic import BaseModel


class OperationalDocumentVersion(BaseModel):
    id: str | None = None
    document_id: str
    version_number: int
    content: str
    updated_at: Any | None = None
    generated_by: str = "system"


class OperationalDocumentVersionCreate(BaseModel):
    document_id: str
    version_number: int
    content: str
    generated_by: str = "admin"
