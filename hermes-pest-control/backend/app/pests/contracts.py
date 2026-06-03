from pydantic import BaseModel


class ClassifiedPest(BaseModel):
    pest_type: str | None = None
    pest_type_spanish: str | None = None
