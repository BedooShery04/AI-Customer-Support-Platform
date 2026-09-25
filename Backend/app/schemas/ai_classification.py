from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import TicketCategory, TicketPriority


# AI output

class AIClassificationContent(BaseModel):
    """
    Structured output expected from the AI model.
    """

    category: TicketCategory
    priority: TicketPriority
    summary: str
    suggested_action: str


# Database record + API output

class AIClassificationResponse(BaseModel):
    """
    API response for a stored AI classification.
    """

    id: int
    ticket_id: int
    category: TicketCategory
    priority: TicketPriority
    summary: str
    suggested_action: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)