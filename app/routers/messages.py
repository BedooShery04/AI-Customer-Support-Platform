from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.message import (
    MessageCreate,
    MessageResponse,
)
from app.services.message_service import MessageService


router = APIRouter(
    prefix="/tickets/{ticket_id}/messages",
    tags=["Messages"],
)


@router.get(
    "",
    response_model=list[MessageResponse],
)
def get_ticket_messages(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MessageService.get_ticket_messages(
        ticket_id=ticket_id,
        user_id=current_user.id,
        user_role=current_user.role,
        db=db,
    )


@router.post(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    ticket_id: int,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MessageService.create_message(
        ticket_id=ticket_id,
        message_data=message_data,
        user_id=current_user.id,
        user_role=current_user.role,
        db=db,
    )