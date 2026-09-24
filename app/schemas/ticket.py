from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import (
    TicketCategory,
    TicketPriority,
    TicketStatus,
)


class TicketCreate(BaseModel):
    subject: str
    description: str
    category: TicketCategory
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketUpdate(BaseModel):
    subject: str | None = None
    description: str | None = None
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    assigned_agent_id: int | None = None


class TicketResponse(BaseModel):
    id: int
    customer_id: int
    assigned_agent_id: int | None

    subject: str
    description: str

    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)