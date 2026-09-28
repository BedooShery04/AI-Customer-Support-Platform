from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.orm import Session

from app.agent.graph import build_graph, model
from app.agent.prompts import (
    AI_CLASSIFICATION_PROMPT,
    AI_RESPONSE_SUGGESTION_PROMPT,
)
from app.enums import UserRole
from app.models.ai_chat_message import AIChatMessage
from app.models.ai_classification import TicketAIClassification
from app.models.audit_log import AuditLog
from app.models.message import Message
from app.models.pending_ticket_draft import PendingTicketDraft
from app.models.user import User
from app.schemas.ai_classification import (
    AIClassificationContent,
    AIClassificationResponse,
)
from app.schemas.ai_suggestion import AISuggestionContent
from app.services import ticket_service


CONFIRMATIONS = {
    "yes",
    "yes create it",
    "yes create them",
    "confirm",
    "confirmed",
    "create it",
    "create them",
    "ايوه",
    "أيوه",
    "نعم",
    "موافق",
    "موافقة",
    "اكد",
    "أكد",
    "اعملها",
    "اعملهم",
}

CANCELLATIONS = {
    "no",
    "cancel",
    "cancel it",
    "cancel them",
    "don't create it",
    "don't create them",
    "لا",
    "لأ",
    "الغاء",
    "إلغاء",
    "الغي",
    "إلغي",
}

DRAFT_EXPIRY = timedelta(minutes=30)


class AIService:

    # =====================================================
    # Chat Helpers
    # =====================================================

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(
            text.strip().casefold().split()
        ).rstrip(".!")

    @staticmethod
    def _draft_expired(
        draft: PendingTicketDraft,
    ) -> bool:
        created_at = draft.created_at

        if created_at.tzinfo is None:
            created_at = created_at.replace(
                tzinfo=timezone.utc
            )

        return (
            datetime.now(timezone.utc) - created_at
            > DRAFT_EXPIRY
        )

    @staticmethod
    def _format_draft(
        tickets: list[dict],
    ) -> str:
        lines = [
            "Please review the proposed ticket details:"
        ]

        for number, item in enumerate(
            tickets,
            start=1,
        ):
            lines.extend([
                "",
                f"Ticket {number}",
                f"Subject: {item['subject']}",
                f"Description: {item['description']}",
            ])

        lines.extend([
            "",
            "Confirm the entire batch by replying "
            "'Yes, create them'.",
            "Or tell me what to change, "
            "or reply 'Cancel'.",
        ])

        return "\n".join(lines)

    @staticmethod
    def _format_pending_draft(
        db: Session,
        draft: PendingTicketDraft,
    ) -> str:
        if draft.customer_id is None:
            return AIService._format_draft(
                draft.tickets
            )

        customer = db.get(
            User,
            draft.customer_id,
        )

        if customer is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Draft customer no longer exists."
                ),
            )

        return "\n".join([
            "Creating tickets on behalf of:",
            f"Customer: {customer.name}",
            f"Email: {customer.email}",
            f"Customer ID: {customer.id}",
            "",
            AIService._format_draft(
                draft.tickets
            ),
        ])

    @staticmethod
    def _save_chat_reply(
        db: Session,
        user_id: int,
        user_message: str,
        assistant_message: str,
    ) -> dict:
        db.add_all([
            AIChatMessage(
                user_id=user_id,
                role="user",
                message=user_message,
            ),
            AIChatMessage(
                user_id=user_id,
                role="assistant",
                message=assistant_message,
            ),
        ])

        db.commit()

        return {
            "message": assistant_message
        }

    @staticmethod
    def _load_conversation(
        db: Session,
        user_id: int,
    ) -> list:
        stored = (
            db.query(AIChatMessage)
            .filter(
                AIChatMessage.user_id == user_id
            )
            .order_by(
                AIChatMessage.id.desc()
            )
            .limit(30)
            .all()
        )

        conversation = []

        for item in reversed(stored):
            if item.role == "user":
                conversation.append(
                    HumanMessage(
                        content=item.message
                    )
                )

            elif item.role == "assistant":
                conversation.append(
                    AIMessage(
                        content=item.message
                    )
                )

        return conversation

    # =====================================================
    # Confirm Ticket Draft
    # =====================================================

    @staticmethod
    def _confirm_draft(
        db: Session,
        user_id: int,
        user_role: UserRole,
        message: str,
    ) -> dict:
        try:
            created = ticket_service.confirm_ticket_draft(
                db=db,
                user_id=user_id,
                user_role=user_role,
                is_expired=AIService._draft_expired,
            )

            if not created:
                reply = (
                    "Your ticket draft has expired. "
                    "Please submit your request again."
                )

            else:
                lines = [
                    f"Successfully created "
                    f"{len(created)} ticket(s):"
                ]

                for item in created:
                    lines.append(
                        f"- Ticket #{item['id']}: "
                        f"{item['subject']}"
                    )

                reply = "\n".join(lines)

        except HTTPException as exc:
            reply = str(exc.detail)

        return AIService._save_chat_reply(
            db=db,
            user_id=user_id,
            user_message=message,
            assistant_message=reply,
        )

    # =====================================================
    # Chat with AI Agent
    # =====================================================

    @staticmethod
    async def chat(
        db: Session,
        user_id: int,
        user_role: UserRole,
        message: str,
        history: list | None = None,
    ) -> dict:
        text = message.strip()

        if not text:
            raise HTTPException(
                status_code=422,
                detail="Message cannot be empty.",
            )

        normalized = AIService._normalize(
            text
        )

        draft = db.get(
            PendingTicketDraft,
            user_id,
        )

        # The backend handles cancellation directly.
        if (
            draft is not None
            and normalized in CANCELLATIONS
        ):
            db.delete(draft)
            db.commit()

            return AIService._save_chat_reply(
                db,
                user_id,
                message,
                "Your draft has been cancelled. "
                "No tickets were created.",
            )

        # Confirmation is never delegated to the LLM.
        if normalized in CONFIRMATIONS:
            return AIService._confirm_draft(
                db=db,
                user_id=user_id,
                user_role=user_role,
                message=message,
            )

        # Remove expired drafts before AI processing.
        if (
            draft is not None
            and AIService._draft_expired(draft)
        ):
            db.delete(draft)
            db.commit()
            draft = None

        conversation = AIService._load_conversation(
            db=db,
            user_id=user_id,
        )

        previous = (
            (
                draft.customer_id,
                list(draft.tickets),
                draft.created_at,
            )
            if draft is not None
            else None
        )

        if draft is not None:
            conversation.append(
                SystemMessage(
                    content=(
                        "There is a pending ticket draft:\n"
                        + AIService._format_pending_draft(
                            db,
                            draft,
                        )
                        + "\nFor revisions, save the COMPLETE "
                        "new draft using the appropriate "
                        "role-specific proposal tool. "
                        "Do not create actual tickets."
                    )
                )
            )

        conversation.append(
            HumanMessage(
                content=message
            )
        )

        graph = build_graph(
            db=db,
            user_id=user_id,
            user_role=user_role,
        )

        result = await graph.ainvoke({
            "messages": conversation,
        })

        messages = result.get(
            "messages",
            [],
        )

        if not messages:
            raise RuntimeError(
                "AI Agent returned no messages."
            )

        reply = str(
            messages[-1].content
        )

        # Refresh the session after tool execution.
        db.expire_all()

        updated = db.get(
            PendingTicketDraft,
            user_id,
        )

        if updated is not None:
            current = (
                updated.customer_id,
                list(updated.tickets),
                updated.created_at,
            )

            if previous != current:
                reply = AIService._format_pending_draft(
                    db,
                    updated,
                )

        return AIService._save_chat_reply(
            db=db,
            user_id=user_id,
            user_message=message,
            assistant_message=reply,
        )

    # =====================================================
    # Get AI Chat History
    # =====================================================

    @staticmethod
    def get_chat_history(
        db: Session,
        user_id: int,
    ):
        return (
            db.query(AIChatMessage)
            .filter(
                AIChatMessage.user_id == user_id
            )
            .order_by(
                AIChatMessage.created_at.asc(),
                AIChatMessage.id.asc(),
            )
            .all()
        )

    # =====================================================
    # Get Ticket Conversation
    # =====================================================

    @staticmethod
    def get_ticket_conversation(
        ticket_id: int,
        db: Session,
    ):
        messages = (
            db.query(Message)
            .filter(
                Message.ticket_id == ticket_id
            )
            .order_by(
                Message.created_at.asc(),
                Message.id.asc(),
            )
            .all()
        )

        return [
            {
                "sender_id": item.sender_id,
                "message": item.message,
                "created_at": (
                    item.created_at.isoformat()
                    if item.created_at
                    else None
                ),
            }
            for item in messages
        ]

    # =====================================================
    # Suggest Response
    # =====================================================

    @staticmethod
    async def suggest_response(
        db: Session,
        ticket_id: int,
        user_id: int,
        user_role: UserRole,
    ):
        if user_role not in (
            UserRole.AGENT,
            UserRole.ADMIN,
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only agents and admins "
                    "can request suggestions."
                ),
            )

        ticket = ticket_service.get_ticket(
            ticket_id=ticket_id,
            user_id=user_id,
            user_role=user_role,
            db=db,
        )

        ticket_data = {
            "ticket_id": ticket.id,
            "subject": ticket.subject,
            "description": ticket.description,
            "category": ticket.category.value,
            "priority": ticket.priority.value,
            "status": ticket.status.value,
            "classification_status": (
                ticket.classification_status
            ),
            "conversation": (
                AIService.get_ticket_conversation(
                    ticket_id=ticket_id,
                    db=db,
                )
            ),
        }

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                AI_RESPONSE_SUGGESTION_PROMPT,
            ),
            (
                "human",
                "Ticket data:\n{data}",
            ),
        ])

        chain = (
            prompt
            | model.with_structured_output(
                AISuggestionContent
            )
        )

        result = await chain.ainvoke({
            "data": str(ticket_data),
        })

        suggestion = (
            AISuggestionContent.model_validate(
                result
            )
        )

        db.add(
            AuditLog(
                admin_id=user_id,
                ticket_id=ticket_id,
                action=(
                    "AI response suggestion generated"
                ),
            )
        )

        db.commit()

        return suggestion.suggestion

    # =====================================================
    # Classify Ticket
    # =====================================================

    @staticmethod
    async def classify_ticket(
        db: Session,
        ticket_id: int,
        user_id: int,
        user_role: UserRole,
    ):
        if user_role not in (
            UserRole.ADMIN,
            UserRole.AGENT,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Only agents and admins "
                    "can classify tickets."
                ),
            )

        ticket = ticket_service.get_ticket(
            ticket_id=ticket_id,
            user_id=user_id,
            user_role=user_role,
            db=db,
        )

        ticket_data = {
            "ticket_id": ticket.id,
            "subject": ticket.subject,
            "description": ticket.description,
            "status": ticket.status.value,
            "conversation": (
                AIService.get_ticket_conversation(
                    ticket_id=ticket_id,
                    db=db,
                )
            ),
        }

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                AI_CLASSIFICATION_PROMPT,
            ),
            (
                "human",
                "Ticket data:\n{data}",
            ),
        ])

        chain = (
            prompt
            | model.with_structured_output(
                AIClassificationContent
            )
        )

        try:
            result = await chain.ainvoke({
                "data": str(ticket_data),
            })

            classification = (
                AIClassificationContent.model_validate(
                    result
                )
            )

        except Exception as exc:
            db.rollback()

            ticket = ticket_service.get_ticket(
                ticket_id=ticket_id,
                user_id=user_id,
                user_role=user_role,
                db=db,
            )

            if ticket.classification_status != "completed":
                ticket.classification_status = "failed"
                db.commit()

            raise HTTPException(
                status_code=502,
                detail=(
                    "AI classification failed. "
                    "Please retry."
                ),
            ) from exc

        try:
            existing = (
                db.query(TicketAIClassification)
                .filter(
                    TicketAIClassification.ticket_id
                    == ticket_id
                )
                .first()
            )

            if existing is None:
                existing = TicketAIClassification(
                    ticket_id=ticket_id,
                    category=classification.category,
                    priority=classification.priority,
                    summary=classification.summary,
                    suggested_action=(
                        classification.suggested_action
                    ),
                )

                db.add(existing)

            else:
                existing.category = (
                    classification.category
                )
                existing.priority = (
                    classification.priority
                )
                existing.summary = (
                    classification.summary
                )
                existing.suggested_action = (
                    classification.suggested_action
                )

            ticket.category = (
                classification.category
            )

            ticket.priority = (
                classification.priority
            )

            ticket.classification_status = (
                "completed"
            )

            db.commit()
            db.refresh(existing)

        except Exception:
            db.rollback()
            raise

        return AIClassificationResponse.model_validate(
            existing
        )