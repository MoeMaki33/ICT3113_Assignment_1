from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class TicketCreate(BaseModel):
    narrative: str

    @field_validator("narrative")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Narrative must not be empty")
        return value


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category: str


class TicketRead(TicketResponse):
    narrative: str
    model: str
    created_at: datetime
