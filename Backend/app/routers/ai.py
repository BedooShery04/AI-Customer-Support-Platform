from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.enums import UserRole
from app.models.user import User
from app.schemas.ai_classification import AIClassificationResponse
from app.schemas.ai_suggestion import AISuggestionContent
from app.schemas.ai_chat import AIChatMessageResponse
from app.services.ai_service import AIService


router = APIRouter(
    prefix="/ai",
    tags=["AI"]
)


# =========================================================
# Request schemas
# =========================================================

class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AIChatRequest(BaseModel):
    message: str
    history: list[ChatHistoryMessage] = Field(default_factory=list)


class AIChatResponse(BaseModel):
    message: str


class AISuggestionRequest(BaseModel):
    ticket_id: int


class AIClassificationRequest(BaseModel):
    ticket_id: int


# =========================================================
# Role dependency
# Agent or Admin
# =========================================================

def require_agent_or_admin(
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in (
        UserRole.AGENT,
        UserRole.ADMIN
    ):
        raise HTTPException(
            status_code=403,
            detail="Only agents and admins can use this AI feature."
        )

    return current_user


# =========================================================
# AI Chat
# Accessible to authenticated users
# =========================================================

@router.post(
    "/chat",
    response_model=AIChatResponse
)
async def chat(
    request: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    history = [
        item.model_dump()
        for item in request.history
    ]

    result = await AIService.chat(
        db=db,
        user_id=current_user.id,
        user_role=current_user.role,
        message=request.message,
        history=history
    )

    return result


@router.get(
    "/chat/messages",
    response_model=list[AIChatMessageResponse]
)
async def get_chat_messages(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return AIService.get_chat_history(
        db=db,
        user_id=current_user.id,
    )

# =========================================================
# AI Response Suggestion
# Agent / Admin only
# =========================================================

@router.post(
    "/suggest-response",
    response_model=AISuggestionContent
)
async def suggest_response(
    request: AISuggestionRequest,
    current_user: User = Depends(require_agent_or_admin),
    db: Session = Depends(get_db)
):
    try:
        suggestion = await AIService.suggest_response(
            db=db,
            ticket_id=request.ticket_id,
            user_id=current_user.id,
            user_role=current_user.role
        )

    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc)
        )

    return AISuggestionContent(
        suggestion=suggestion
    )


# =========================================================
# AI Ticket Classification
# Agent / Admin only
# =========================================================

@router.post(
    "/classify-ticket",
    response_model=AIClassificationResponse
)
async def classify_ticket(
    request: AIClassificationRequest,
    current_user: User = Depends(require_agent_or_admin),
    db: Session = Depends(get_db)
):
    result = await AIService.classify_ticket(
        db=db,
        ticket_id=request.ticket_id,
        user_id=current_user.id,
        user_role=current_user.role
    )

    return result