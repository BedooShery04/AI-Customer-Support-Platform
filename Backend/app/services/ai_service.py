
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
from app.models.ai_chat import AIChat
from app.models.ai_chat_message import AIChatMessage
from app.models.ai_classification import TicketAIClassification
from app.models.audit_log import AuditLog
from app.models.message import Message
from app.models.pending_ticket_draft import PendingTicketDraft
from app.models.pending_ticket_update import PendingTicketUpdate
from app.models.ticket import Ticket
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
    "confirm update",
    "confirm edit",
    "save changes",
    "yes save changes",
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
    "احفظ التعديل",
    "احفظ التعديلات",
}

CANCELLATIONS = {
    "no",
    "cancel",
    "cancel it",
    "cancel them",
    "cancel update",
    "cancel edit",
    "don't create it",
    "don't create them",
    "لا",
    "لأ",
    "الغاء",
    "إلغاء",
    "الغي",
    "إلغي",
    "الغي التعديل",
    "إلغي التعديل",
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
        ).rstrip(".!،؟?")

    @staticmethod
    def _get_user_chat(
        db: Session,
        user_id: int,
        chat_id: int,
    ) -> AIChat:
        chat = (
            db.query(AIChat)
            .filter(
                AIChat.id == chat_id,
                AIChat.user_id == user_id,
            )
            .first()
        )

        if chat is None:
            raise HTTPException(
                status_code=404,
                detail="Chat not found.",
            )

        return chat

    @staticmethod
    def _draft_expired(
        draft: PendingTicketDraft | PendingTicketUpdate,
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
                detail="Draft customer no longer exists.",
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
    def _format_ticket_update(
        db: Session,
        draft: PendingTicketUpdate,
    ) -> str:
        ticket = db.get(
            Ticket,
            draft.ticket_id,
        )

        if ticket is None:
            return (
                "The ticket for this draft no longer exists. "
                "Cancel the draft before starting another edit."
            )

        lines = [
            f"Please review your changes to ticket #{ticket.id}:"
        ]

        if draft.subject is not None:
            lines.extend([
                "",
                f"Current subject: {ticket.subject}",
                f"New subject: {draft.subject}",
            ])

        if draft.description is not None:
            lines.extend([
                "",
                f"Current description: {ticket.description}",
                f"New description: {draft.description}",
            ])

        lines.extend([
            "",
            "No changes have been applied yet.",
            "Reply 'Confirm' to save these changes, "
            "or 'Cancel' to discard them.",
            "You can also tell me what to change.",
        ])

        return "\n".join(lines)

    @staticmethod
    def _save_chat_reply(
        db: Session,
        user_id: int,
        chat_id: int,
        user_message: str,
        assistant_message: str,
    ) -> dict:
        db.add_all([
            AIChatMessage(
                user_id=user_id,
                chat_id=chat_id,
                role="user",
                message=user_message,
            ),
            AIChatMessage(
                user_id=user_id,
                chat_id=chat_id,
                role="assistant",
                message=assistant_message,
            ),
        ])

        chat = AIService._get_user_chat(
            db=db,
            user_id=user_id,
            chat_id=chat_id,
        )

        chat.updated_at = datetime.utcnow()

        db.commit()

        return {
            "message": assistant_message,
        }

    @staticmethod
    def _load_conversation(
        db: Session,
        user_id: int,
        chat_id: int,
    ) -> list:
        stored = (
            db.query(AIChatMessage)
            .filter(
                AIChatMessage.user_id == user_id,
                AIChatMessage.chat_id == chat_id,
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
    # Confirm Ticket Creation Draft
    # =====================================================

    @staticmethod
    def _confirm_draft(
        db: Session,
        user_id: int,
        chat_id: int,
        user_role: UserRole,
        message: str,
    ) -> dict:
        try:
            created = ticket_service.confirm_ticket_draft(
                db=db,
                user_id=user_id,
                chat_id=chat_id,
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
            chat_id=chat_id,
            user_message=message,
            assistant_message=reply,
        )

    # =====================================================
    # Confirm Ticket Update Draft
    # =====================================================

    @staticmethod
    def _confirm_ticket_update(
        db: Session,
        user_id: int,
        chat_id: int,
        user_role: UserRole,
        message: str,
    ) -> dict:
        try:
            ticket = ticket_service.confirm_customer_ticket_update(
                db=db,
                user_id=user_id,
                chat_id=chat_id,
                user_role=user_role,
                is_expired=AIService._draft_expired,
            )

            reply = (
                f"Ticket #{ticket.id} was updated successfully."
            )

        except HTTPException as exc:
            reply = str(exc.detail)

        return AIService._save_chat_reply(
            db=db,
            user_id=user_id,
            chat_id=chat_id,
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
        chat_id: int,
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

        AIService._get_user_chat(
            db=db,
            user_id=user_id,
            chat_id=chat_id,
        )

        normalized = AIService._normalize(text)

        # Load pending operations from this chat only.
        draft = db.get(
            PendingTicketDraft,
            (user_id, chat_id),
        )

        edit_draft = db.get(
            PendingTicketUpdate,
            (user_id, chat_id),
        )

        expired_creation = (
            draft is not None
            and AIService._draft_expired(draft)
        )

        expired_edit = (
            edit_draft is not None
            and AIService._draft_expired(edit_draft)
        )

        if expired_creation or expired_edit:
            if expired_creation:
                db.delete(draft)
                draft = None

            if expired_edit:
                db.delete(edit_draft)
                edit_draft = None

            db.commit()

            if normalized in CONFIRMATIONS:
                return AIService._save_chat_reply(
                    db=db,
                    user_id=user_id,
                    chat_id=chat_id,
                    user_message=message,
                    assistant_message=(
                        "Your pending draft has expired. "
                        "Please submit your request again."
                    ),
                )

        # Do not guess when both operation types exist.
        if draft is not None and edit_draft is not None:
            if (
                normalized in CONFIRMATIONS
                or normalized in CANCELLATIONS
            ):
                return AIService._save_chat_reply(
                    db=db,
                    user_id=user_id,
                    chat_id=chat_id,
                    user_message=message,
                    assistant_message=(
                        "You have both a ticket creation draft "
                        "and a ticket edit draft in this chat. "
                        "Please specify which operation you "
                        "want to confirm or cancel."
                    ),
                )

        # Cancel only drafts belonging to this chat.
        if normalized in CANCELLATIONS:
            if draft is not None:
                db.delete(draft)
                db.commit()

                return AIService._save_chat_reply(
                    db=db,
                    user_id=user_id,
                    chat_id=chat_id,
                    user_message=message,
                    assistant_message=(
                        "Your ticket creation draft "
                        "has been cancelled. "
                        "No tickets were created."
                    ),
                )

            if edit_draft is not None:
                db.delete(edit_draft)
                db.commit()

                return AIService._save_chat_reply(
                    db=db,
                    user_id=user_id,
                    chat_id=chat_id,
                    user_message=message,
                    assistant_message=(
                        "Your ticket edit draft "
                        "has been cancelled. "
                        "No changes were applied."
                    ),
                )

        # Confirm only drafts belonging to this chat.
        if normalized in CONFIRMATIONS:
            if edit_draft is not None:
                return AIService._confirm_ticket_update(
                    db=db,
                    user_id=user_id,
                    chat_id=chat_id,
                    user_role=user_role,
                    message=message,
                )

            if draft is not None:
                return AIService._confirm_draft(
                    db=db,
                    user_id=user_id,
                    chat_id=chat_id,
                    user_role=user_role,
                    message=message,
                )

            return AIService._save_chat_reply(
                db=db,
                user_id=user_id,
                chat_id=chat_id,
                user_message=message,
                assistant_message=(
                    "There is no pending operation "
                    "to confirm in this chat."
                ),
            )

        conversation = AIService._load_conversation(
            db=db,
            user_id=user_id,
            chat_id=chat_id,
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

        previous_edit = (
            (
                edit_draft.ticket_id,
                edit_draft.subject,
                edit_draft.description,
                edit_draft.created_at,
            )
            if edit_draft is not None
            else None
        )

        if draft is not None:
            conversation.append(
                SystemMessage(
                    content=(
                        "There is a pending ticket creation "
                        "draft in this chat:\n"
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

        if edit_draft is not None:
            conversation.append(
                SystemMessage(
                    content=(
                        "There is a pending ticket edit "
                        "draft in this chat:\n"
                        + AIService._format_ticket_update(
                            db,
                            edit_draft,
                        )
                        + "\nFor revisions, use "
                        "propose_ticket_update to save the "
                        "complete revised proposal. "
                        "Do not apply changes directly. "
                        "The backend handles confirmation."
                    )
                )
            )

        conversation.append(
            HumanMessage(
                content=message
            )
        )

        # The graph and its tools must also receive chat_id.
        # Update build_graph in the next step.
        graph = build_graph(
            db=db,
            user_id=user_id,
            chat_id=chat_id,
            user_role=user_role,
        )

        result = await graph.ainvoke({
            "messages": conversation,
        })

        result_messages = result.get(
            "messages",
            [],
        )

        if not result_messages:
            raise RuntimeError(
                "AI Agent returned no messages."
            )

        reply = str(
            result_messages[-1].content
        )

        # Reload drafts created or revised by the tools.
        db.expire_all()

        updated = db.get(
            PendingTicketDraft,
            (user_id, chat_id),
        )

        updated_edit = db.get(
            PendingTicketUpdate,
            (user_id, chat_id),
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

        if updated_edit is not None:
            current_edit = (
                updated_edit.ticket_id,
                updated_edit.subject,
                updated_edit.description,
                updated_edit.created_at,
            )

            if previous_edit != current_edit:
                reply = AIService._format_ticket_update(
                    db,
                    updated_edit,
                )

        return AIService._save_chat_reply(
            db=db,
            user_id=user_id,
            chat_id=chat_id,
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
        chat_id: int,
    ):
        AIService._get_user_chat(
            db=db,
            user_id=user_id,
            chat_id=chat_id,
        )

        return (
            db.query(AIChatMessage)
            .filter(
                AIChatMessage.user_id == user_id,
                AIChatMessage.chat_id == chat_id,
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
                action="AI response suggestion generated",
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