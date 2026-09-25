from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: int
    admin_id: int
    ticket_id: int
    action: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)