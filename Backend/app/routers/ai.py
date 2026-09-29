
from datetime import datetime
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.enums import UserRole
from app.models.ai_chat import AIChat
from app.models.user import User
from app.schemas.ai_classification import AIClassificationResponse
from app.schemas.ai_suggestion import AISuggestionContent
from app.schemas.ai_chat import AIChatMessageResponse
from app.services.ai_service import AIService


router = APIRouter(
    prefix="/ai",
    tags=["AI"],
)


# =========================================================
# Request and Response Schemas
# =========================================================

class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AIChatRequest(BaseModel):
    chat_id: int = Field(gt=0)
    message: str = Field(min_length=1)
    history: list[ChatHistoryMessage] = Field(
        default_factory=list
    )


class AIChatResponse(BaseModel):
    message: str


class AIChatCreateRequest(BaseModel):
    title: str = Field(
        default="New Chat",
        min_length=1,
        max_length=255,
    )


class AIChatRenameRequest(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
    )


class AIChatDetailsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class PendingCustomerResponse(BaseModel):
    id: int
    name: str
    email: str


class PendingTicketResponse(BaseModel):
    subject: str
    description: str


class PendingTicketCreationResponse(BaseModel):
    type: Literal["ticket_creation"]
    status: Literal["pending"]
    expires_at: datetime
    customer: PendingCustomerResponse | None
    tickets: list[PendingTicketResponse]


class PendingTicketUpdateResponse(BaseModel):
    type: Literal["ticket_update"]
    status: Literal["pending"]
    expires_at: datetime
    ticket_id: int
    current_subject: str | None
    current_description: str | None
    new_subject: str | None
    new_description: str | None


class PendingOperationResponse(BaseModel):
    chat_id: int
    pending_operation: (
        PendingTicketCreationResponse
        | PendingTicketUpdateResponse
        | None
    )


class AISuggestionRequest(BaseModel):
    ticket_id: int


class AIClassificationRequest(BaseModel):
    ticket_id: int


# =========================================================
# Dependencies
# =========================================================

def require_agent_or_admin(
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (
        UserRole.AGENT,
        UserRole.ADMIN,
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Only agents and admins "
                "can use this AI feature."
            ),
        )

    return current_user


def get_owned_chat(
    chat_id: int,
    current_user: User,
    db: Session,
) -> AIChat:
    chat = (
        db.query(AIChat)
        .filter(
            AIChat.id == chat_id,
            AIChat.user_id == current_user.id,
        )
        .first()
    )

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found.",
        )

    return chat


# =========================================================
# Create Chat
# =========================================================

@router.post(
    "/chats",
    response_model=AIChatDetailsResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_chat(
    request: AIChatCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    title = request.title.strip()

    if not title:
        raise HTTPException(
            status_code=422,
            detail="Chat title cannot be empty.",
        )

    chat = AIChat(
        user_id=current_user.id,
        title=title,
    )

    db.add(chat)
    db.commit()
    db.refresh(chat)

    return chat


# =========================================================
# List Chats
# =========================================================

@router.get(
    "/chats",
    response_model=list[AIChatDetailsResponse],
)
def list_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(AIChat)
        .filter(
            AIChat.user_id == current_user.id,
        )
        .order_by(
            AIChat.updated_at.desc(),
            AIChat.id.desc(),
        )
        .all()
    )


# =========================================================
# Get Chat Details
# =========================================================

@router.get(
    "/chats/{chat_id}",
    response_model=AIChatDetailsResponse,
)
def get_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_owned_chat(
        chat_id=chat_id,
        current_user=current_user,
        db=db,
    )


# =========================================================
# Rename Chat
# =========================================================

@router.patch(
    "/chats/{chat_id}",
    response_model=AIChatDetailsResponse,
)
def rename_chat(
    chat_id: int,
    request: AIChatRenameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat = get_owned_chat(
        chat_id=chat_id,
        current_user=current_user,
        db=db,
    )

    title = request.title.strip()

    if not title:
        raise HTTPException(
            status_code=422,
            detail="Chat title cannot be empty.",
        )

    chat.title = title
    chat.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(chat)

    return chat


# =========================================================
# Delete Chat
# =========================================================

@router.delete(
    "/chats/{chat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat = get_owned_chat(
        chat_id=chat_id,
        current_user=current_user,
        db=db,
    )

    db.delete(chat)
    db.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


# =========================================================
# Get Messages for a Specific Chat
# =========================================================

@router.get(
    "/chats/{chat_id}/messages",
    response_model=list[AIChatMessageResponse],
)
def get_chat_messages(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AIService.get_chat_history(
        db=db,
        user_id=current_user.id,
        chat_id=chat_id,
    )


# =========================================================
# Get Pending Operation for a Specific Chat
# =========================================================

@router.get(
    "/chats/{chat_id}/pending-operation",
    response_model=PendingOperationResponse,
)
def get_pending_operation(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_chat(
        chat_id=chat_id,
        current_user=current_user,
        db=db,
    )

    return AIService.get_pending_operation(
        db=db,
        user_id=current_user.id,
        chat_id=chat_id,
    )


# =========================================================
# AI Chat
# =========================================================

@router.post(
    "/chat",
    response_model=AIChatResponse,
)
async def chat(
    request: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_chat(
        chat_id=request.chat_id,
        current_user=current_user,
        db=db,
    )

    history = [
        item.model_dump()
        for item in request.history
    ]

    return await AIService.chat(
        db=db,
        user_id=current_user.id,
        chat_id=request.chat_id,
        user_role=current_user.role,
        message=request.message,
        history=history,
    )


# =========================================================
# AI Response Suggestion
# Agent / Admin only
# =========================================================

@router.post(
    "/suggest-response",
    response_model=AISuggestionContent,
)
async def suggest_response(
    request: AISuggestionRequest,
    current_user: User = Depends(require_agent_or_admin),
    db: Session = Depends(get_db),
):
    try:
        suggestion = await AIService.suggest_response(
            db=db,
            ticket_id=request.ticket_id,
            user_id=current_user.id,
            user_role=current_user.role,
        )

    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        ) from exc

    return AISuggestionContent(
        suggestion=suggestion
    )


# =========================================================
# AI Ticket Classification
# Agent / Admin only
# =========================================================

@router.post(
    "/classify-ticket",
    response_model=AIClassificationResponse,
)
async def classify_ticket(
    request: AIClassificationRequest,
    current_user: User = Depends(require_agent_or_admin),
    db: Session = Depends(get_db),
):
    return await AIService.classify_ticket(
        db=db,
        ticket_id=request.ticket_id,
        user_id=current_user.id,
        user_role=current_user.role,
    )
from datetime import datetime
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.enums import UserRole
from app.models.ai_chat import AIChat
from app.models.user import User
from app.schemas.ai_classification import AIClassificationResponse
from app.schemas.ai_suggestion import AISuggestionContent
from app.schemas.ai_chat import AIChatMessageResponse
from app.services.ai_service import AIService


router = APIRouter(
    prefix="/ai",
    tags=["AI"],
)


# =========================================================
# Request and Response Schemas
# =========================================================

class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AIChatRequest(BaseModel):
    chat_id: int = Field(gt=0)
    message: str = Field(min_length=1)
    history: list[ChatHistoryMessage] = Field(
        default_factory=list
    )


class AIChatResponse(BaseModel):
    message: str


class AIChatCreateRequest(BaseModel):
    title: str = Field(
        default="New Chat",
        min_length=1,
        max_length=255,
    )


class AIChatRenameRequest(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
    )


class AIChatDetailsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class PendingCustomerResponse(BaseModel):
    id: int
    name: str
    email: str


class PendingTicketResponse(BaseModel):
    subject: str
    description: str


class PendingTicketCreationResponse(BaseModel):
    type: Literal["ticket_creation"]
    status: Literal["pending"]
    expires_at: datetime
    customer: PendingCustomerResponse | None
    tickets: list[PendingTicketResponse]


class PendingTicketUpdateResponse(BaseModel):
    type: Literal["ticket_update"]
    status: Literal["pending"]
    expires_at: datetime
    ticket_id: int
    current_subject: str | None
    current_description: str | None
    new_subject: str | None
    new_description: str | None


class PendingOperationResponse(BaseModel):
    chat_id: int
    pending_operation: (
        PendingTicketCreationResponse
        | PendingTicketUpdateResponse
        | None
    )


class AISuggestionRequest(BaseModel):
    ticket_id: int


class AIClassificationRequest(BaseModel):
    ticket_id: int


# =========================================================
# Dependencies
# =========================================================

def require_agent_or_admin(
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (
        UserRole.AGENT,
        UserRole.ADMIN,
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Only agents and admins "
                "can use this AI feature."
            ),
        )

    return current_user


def get_owned_chat(
    chat_id: int,
    current_user: User,
    db: Session,
) -> AIChat:
    chat = (
        db.query(AIChat)
        .filter(
            AIChat.id == chat_id,
            AIChat.user_id == current_user.id,
        )
        .first()
    )

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found.",
        )

    return chat


# =========================================================
# Create Chat
# =========================================================

@router.post(
    "/chats",
    response_model=AIChatDetailsResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_chat(
    request: AIChatCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    title = request.title.strip()

    if not title:
        raise HTTPException(
            status_code=422,
            detail="Chat title cannot be empty.",
        )

    chat = AIChat(
        user_id=current_user.id,
        title=title,
    )

    db.add(chat)
    db.commit()
    db.refresh(chat)

    return chat


# =========================================================
# List Chats
# =========================================================

@router.get(
    "/chats",
    response_model=list[AIChatDetailsResponse],
)
def list_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(AIChat)
        .filter(
            AIChat.user_id == current_user.id,
        )
        .order_by(
            AIChat.updated_at.desc(),
            AIChat.id.desc(),
        )
        .all()
    )


# =========================================================
# Get Chat Details
# =========================================================

@router.get(
    "/chats/{chat_id}",
    response_model=AIChatDetailsResponse,
)
def get_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_owned_chat(
        chat_id=chat_id,
        current_user=current_user,
        db=db,
    )


# =========================================================
# Rename Chat
# =========================================================

@router.patch(
    "/chats/{chat_id}",
    response_model=AIChatDetailsResponse,
)
def rename_chat(
    chat_id: int,
    request: AIChatRenameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat = get_owned_chat(
        chat_id=chat_id,
        current_user=current_user,
        db=db,
    )

    title = request.title.strip()

    if not title:
        raise HTTPException(
            status_code=422,
            detail="Chat title cannot be empty.",
        )

    chat.title = title
    chat.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(chat)

    return chat


# =========================================================
# Delete Chat
# =========================================================

@router.delete(
    "/chats/{chat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat = get_owned_chat(
        chat_id=chat_id,
        current_user=current_user,
        db=db,
    )

    db.delete(chat)
    db.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


# =========================================================
# Get Messages for a Specific Chat
# =========================================================

@router.get(
    "/chats/{chat_id}/messages",
    response_model=list[AIChatMessageResponse],
)
def get_chat_messages(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AIService.get_chat_history(
        db=db,
        user_id=current_user.id,
        chat_id=chat_id,
    )


# =========================================================
# Get Pending Operation for a Specific Chat
# =========================================================

@router.get(
    "/chats/{chat_id}/pending-operation",
    response_model=PendingOperationResponse,
)
def get_pending_operation(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_chat(
        chat_id=chat_id,
        current_user=current_user,
        db=db,
    )

    return AIService.get_pending_operation(
        db=db,
        user_id=current_user.id,
        chat_id=chat_id,
    )


# =========================================================
# AI Chat
# =========================================================

@router.post(
    "/chat",
    response_model=AIChatResponse,
)
async def chat(
    request: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_chat(
        chat_id=request.chat_id,
        current_user=current_user,
        db=db,
    )

    history = [
        item.model_dump()
        for item in request.history
    ]

    return await AIService.chat(
        db=db,
        user_id=current_user.id,
        chat_id=request.chat_id,
        user_role=current_user.role,
        message=request.message,
        history=history,
    )


# =========================================================
# AI Response Suggestion
# Agent / Admin only
# =========================================================

@router.post(
    "/suggest-response",
    response_model=AISuggestionContent,
)
async def suggest_response(
    request: AISuggestionRequest,
    current_user: User = Depends(require_agent_or_admin),
    db: Session = Depends(get_db),
):
    try:
        suggestion = await AIService.suggest_response(
            db=db,
            ticket_id=request.ticket_id,
            user_id=current_user.id,
            user_role=current_user.role,
        )

    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        ) from exc

    return AISuggestionContent(
        suggestion=suggestion
    )


# =========================================================
# AI Ticket Classification
# Agent / Admin only
# =========================================================

@router.post(
    "/classify-ticket",
    response_model=AIClassificationResponse,
)
async def classify_ticket(
    request: AIClassificationRequest,
    current_user: User = Depends(require_agent_or_admin),
    db: Session = Depends(get_db),
):
    return await AIService.classify_ticket(
        db=db,
        ticket_id=request.ticket_id,
        user_id=current_user.id,
        user_role=current_user.role,
    )