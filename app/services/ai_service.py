from sqlalchemy.orm import Session

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate

from app.enums import UserRole

from app.agent.graph import build_graph, model
from app.agent.prompts import (
    AI_RESPONSE_SUGGESTION_PROMPT,
    AI_CLASSIFICATION_PROMPT,
)

from app.models.message import Message
from app.models.ai_classification import TicketAIClassification

from app.schemas.ai_classification import (
    AIClassificationContent,
    AIClassificationResponse,
)

from app.schemas.ai_suggestion import AISuggestionContent

from app.services import ticket_service


class AIService:

    # =========================================================
    # 1 Chat with AI Agent
    # =========================================================

    @staticmethod
    async def chat(
        db: Session,
        user_id: int,
        user_role: UserRole,
        message: str,
        history: list | None = None,
    ):
        """
        Send a message to the AI Agent.

        The current user's ID and role come from authentication.
        """

        # -----------------------------------------------------
        # Prepare conversation history
        # -----------------------------------------------------

        conversation = []

        if history:

            for item in history:

                if item["role"] == "user":

                    conversation.append(
                        HumanMessage(
                            content=item["content"]
                        )
                    )

                elif item["role"] == "assistant":

                    conversation.append(
                        AIMessage(
                            content=item["content"]
                        )
                    )

        # Add the new user message
        conversation.append(
            HumanMessage(
                content=message
            )
        )

        # -----------------------------------------------------
        # Build the AI Agent
        # -----------------------------------------------------

        graph = build_graph(
            db=db,
            user_id=user_id,
            user_role=user_role,
        )

        # -----------------------------------------------------
        # Run the Agent
        # -----------------------------------------------------

        result = await graph.ainvoke(
            {
                "messages": conversation
            }
        )

        # -----------------------------------------------------
        # Get final AI response
        # -----------------------------------------------------

        messages = result.get("messages", [])

        if not messages:
            raise RuntimeError(
                "AI Agent returned no messages."
            )

        final_message = messages[-1]

        return {
            "message": final_message.content
        }

    # =========================================================
    # 2 Get Ticket Conversation
    # =========================================================

    @staticmethod
    def get_ticket_conversation(
        ticket_id: int,
        db: Session,
    ):
        """
        Get all messages belonging to a specific ticket.
        """

        messages = (
            db.query(Message)
            .filter(Message.ticket_id == ticket_id)
            .order_by(Message.created_at.asc())
            .all()
        )

        conversation = []

        for message in messages:

            conversation.append(
                {
                    "sender_id": message.sender_id,
                    "message": message.message,
                    "created_at": message.created_at.isoformat(),
                }
            )

        return conversation

    # =========================================================
    # 3 Suggest Response
    # =========================================================

    @staticmethod
    async def suggest_response(
        db: Session,
        ticket_id: int,
        user_id: int,
        user_role: UserRole,
    ):
        """
        Generate an AI response suggestion for a support agent.

        The AI creates only a draft.
        It does not send the message automatically.
        """

        # -----------------------------------------------------
        # Check user role
        # -----------------------------------------------------

        if user_role not in (
            UserRole.AGENT,
            UserRole.ADMIN,
        ):
            raise PermissionError(
                "Only agents and admins can request AI suggestions."
            )

        # -----------------------------------------------------
        # Get ticket
        # -----------------------------------------------------

        ticket = ticket_service.get_ticket(
            ticket_id=ticket_id,
            user_id=user_id,
            user_role=user_role,
            db=db,
        )

        # -----------------------------------------------------
        # Get ticket conversation
        # -----------------------------------------------------

        conversation = AIService.get_ticket_conversation(
            ticket_id=ticket_id,
            db=db,
        )

        # -----------------------------------------------------
        # Prepare data for AI
        # -----------------------------------------------------

        ticket_data = {
            "ticket_id": ticket.id,
            "subject": ticket.subject,
            "description": ticket.description,
            "category": ticket.category.value,
            "priority": ticket.priority.value,
            "status": ticket.status.value,
            "conversation": conversation,
        }

        # -----------------------------------------------------
        # Create prompt
        # -----------------------------------------------------

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    AI_RESPONSE_SUGGESTION_PROMPT,
                ),
                (
                    "human",
                    "Ticket data:\n{data}",
                ),
            ]
        )

        # -----------------------------------------------------
        # Create structured-output chain
        # -----------------------------------------------------

        chain = (
            prompt
            | model.with_structured_output(
                AISuggestionContent
            )
        )

        # -----------------------------------------------------
        # Ask AI
        # -----------------------------------------------------

        result = await chain.ainvoke(
            {
                "data": str(ticket_data)
            }
        )

        # -----------------------------------------------------
        # Validate AI result
        # -----------------------------------------------------

        suggestion = AISuggestionContent.model_validate(
            result
        )

        # Return only the suggestion text
        return suggestion.suggestion

    # =========================================================
    # 4 Classify Ticket
    # =========================================================

    @staticmethod
    async def classify_ticket(
        db: Session,
        ticket_id: int,
        user_id: int,
        user_role: UserRole,
    ):
        """
        Classify a ticket using AI and save the result
        in the PostgreSQL database.
        """

        # -----------------------------------------------------
        # Get ticket and check authorization
        # -----------------------------------------------------

        ticket = ticket_service.get_ticket(
            ticket_id=ticket_id,
            user_id=user_id,
            user_role=user_role,
            db=db,
        )

        # -----------------------------------------------------
        # Prepare ticket data
        # -----------------------------------------------------

        ticket_data = {
            "ticket_id": ticket.id,
            "subject": ticket.subject,
            "description": ticket.description,
            "category": ticket.category.value,
            "priority": ticket.priority.value,
            "status": ticket.status.value,
        }

        # -----------------------------------------------------
        # Create prompt
        # -----------------------------------------------------

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    AI_CLASSIFICATION_PROMPT,
                ),
                (
                    "human",
                    "Ticket data:\n{data}",
                ),
            ]
        )

        # -----------------------------------------------------
        # Create structured-output chain
        # -----------------------------------------------------

        chain = (
            prompt
            | model.with_structured_output(
                AIClassificationContent
            )
        )

        # -----------------------------------------------------
        # Ask AI
        # -----------------------------------------------------

        result = await chain.ainvoke(
            {
                "data": str(ticket_data)
            }
        )

        # -----------------------------------------------------
        # Validate AI result
        # -----------------------------------------------------

        classification = AIClassificationContent.model_validate(
            result
        )

        # -----------------------------------------------------
        # Check if classification already exists
        # -----------------------------------------------------

        existing = (
            db.query(TicketAIClassification)
            .filter(
                TicketAIClassification.ticket_id == ticket_id
            )
            .first()
        )

        # -----------------------------------------------------
        # Update existing classification
        # -----------------------------------------------------

        if existing:

            existing.category = classification.category
            existing.priority = classification.priority
            existing.summary = classification.summary
            existing.suggested_action = (
                classification.suggested_action
            )

            db.commit()
            db.refresh(existing)

            return AIClassificationResponse.model_validate(
                existing
            )

        # -----------------------------------------------------
        # Create new classification
        # -----------------------------------------------------

        new_classification = TicketAIClassification(
            ticket_id=ticket_id,
            category=classification.category,
            priority=classification.priority,
            summary=classification.summary,
            suggested_action=classification.suggested_action,
        )

        db.add(new_classification)

        db.commit()
        db.refresh(new_classification)

        return AIClassificationResponse.model_validate(
            new_classification
        )