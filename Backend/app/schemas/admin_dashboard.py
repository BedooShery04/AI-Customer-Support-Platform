from pydantic import BaseModel

from app.schemas.ticket import TicketResponse


class SupportActivity(BaseModel):
    agent_id: int
    agent_name: str
    assigned_tickets: int


class AIActivity(BaseModel):
    classified_tickets: int
    chat_requests: int
    suggestions: int


class AdminDashboardResponse(BaseModel):
    total: int
    open: int
    in_progress: int
    resolved: int
    critical: int

    recent_tickets: list[TicketResponse]

    tickets_by_category: dict[str, int]
    tickets_by_status: dict[str, int]
    tickets_by_agent: dict[str, int]
    average_tickets_per_category: float

    support_activity: list[SupportActivity]
    ai_activity: AIActivity