from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    StringConstraints
)

from app.enums import (
    TicketCategory,
    TicketPriority,
    TicketStatus,
)
from typing import Annotated


TicketSubject = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=5,
        max_length=200,
    ),
]

TicketDescription = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=10,
        max_length=5000,
    ),
]

class TicketCreate(BaseModel):
    subject: TicketSubject
    description: TicketDescription

    model_config = ConfigDict(extra="forbid")


class TicketUpdate(BaseModel):
    subject: TicketSubject | None = None
    description: TicketDescription | None = None
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    assigned_agent_id: int | None = Field(
        default=None,
        gt=0,
    )

    model_config = ConfigDict(extra="forbid")

class TicketCustomerInfo(BaseModel):
    id: int
    name: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class TicketAIClassificationInfo(BaseModel):
    category: str
    priority: str
    summary: str
    suggested_action: str

    model_config = ConfigDict(from_attributes=True)


class TicketResponse(BaseModel):
    id: int
    customer_id: int
    customer: TicketCustomerInfo | None = None
    assigned_agent_id: int | None

    subject: str
    description: str

    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus

    created_at: datetime
    updated_at: datetime
    classification_status: str

    ai_classification: TicketAIClassificationInfo | None = None

    model_config = ConfigDict(from_attributes=True)