from datetime import datetime
from pydantic import BaseModel


class AIChatMessageResponse(BaseModel):
    id: int
    role: str
    message: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }