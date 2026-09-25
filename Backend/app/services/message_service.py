from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.enums import UserRole
from app.models.message import Message
from app.schemas.message import MessageCreate
from app.services import ticket_service


class MessageService:

    @staticmethod
    def get_ticket_messages(
        ticket_id: int,
        user_id: int,
        user_role: UserRole,
        db: Session,
    ):
        # Check that the ticket exists and the user
        # is allowed to access it.
        ticket_service.get_ticket(
            ticket_id=ticket_id,
            user_id=user_id,
            user_role=user_role,
            db=db,
        )

        messages = (
            db.query(Message)
            .filter(Message.ticket_id == ticket_id)
            .order_by(
                Message.created_at.asc(),
                Message.id.asc(),
            )
            .all()
        )

        return messages

    @staticmethod
    def create_message(
        ticket_id: int,
        message_data: MessageCreate,
        user_id: int,
        user_role: UserRole,
        db: Session,
    ):
        # Check ticket access before sending a message.
        ticket_service.get_ticket(
            ticket_id=ticket_id,
            user_id=user_id,
            user_role=user_role,
            db=db,
        )

        # Reject empty or whitespace-only messages.
        message_text = message_data.message.strip()

        if not message_text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Message cannot be empty.",
            )

        new_message = Message(
            ticket_id=ticket_id,
            sender_id=user_id,
            message=message_text,
        )

        try:
            db.add(new_message)
            db.commit()
            db.refresh(new_message)

        except Exception:
            db.rollback()
            raise

        return new_message