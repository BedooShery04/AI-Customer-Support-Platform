from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MessageCreate(BaseModel):
    message: str


class MessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender_id: int
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)