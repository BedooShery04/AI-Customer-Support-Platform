from datetime import datetime, timezone

from fastapi import HTTPException
from langchain_core.tools import tool
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.enums import UserRole
from app.enums.user import UserStatus
from app.models.audit_log import AuditLog
from app.models.pending_ticket_draft import PendingTicketDraft
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.services import ticket_service


class ProposedTicket(BaseModel):
    subject: str = Field(
        min_length=5,
        max_length=200,
    )

    description: str = Field(
        min_length=10,
        max_length=5000,
    )


def _ticket_to_dict(ticket):
    return {
        "id": ticket.id,
        "customer_id": ticket.customer_id,
        "assigned_agent_id": ticket.assigned_agent_id,
        "subject": ticket.subject,
        "description": ticket.description,
        "category": ticket.category.value,
        "priority": ticket.priority.value,
        "status": ticket.status.value,
        "classification_status": ticket.classification_status,
        "created_at": (
            ticket.created_at.isoformat()
            if ticket.created_at else None
        ),
        "updated_at": (
            ticket.updated_at.isoformat()
            if ticket.updated_at else None
        ),
    }


def _error_result(exc: HTTPException):
    return {
        "success": False,
        "status_code": exc.status_code,
        "message": str(exc.detail),
    }


def build_tools(
    db: Session,
    user_id: int,
    user_role: UserRole,
):
    """
    Build tools according to the authenticated user's role.
    """

    verified_customer_ids: set[int] = set()

    # ====================================================
    # Customer Tickets
    # ====================================================

    @tool
    def get_customer_tickets():
        """Retrieve the authenticated customer's tickets."""
        try:
            tickets = ticket_service.get_customer_tickets(
                customer_id=user_id,
                user_id=user_id,
                user_role=user_role,
                db=db,
            )

            return {
                "success": True,
                "tickets": [
                    _ticket_to_dict(ticket)
                    for ticket in tickets
                ],
            }

        except HTTPException as exc:
            return _error_result(exc)

    # ====================================================
    # Ticket Details
    # ====================================================

    @tool
    def get_ticket_details(ticket_id: int):
        """Retrieve an accessible ticket's details."""
        try:
            ticket = ticket_service.get_ticket(
                ticket_id=ticket_id,
                user_id=user_id,
                user_role=user_role,
                db=db,
            )

            return {
                "success": True,
                "ticket": _ticket_to_dict(ticket),
            }

        except HTTPException as exc:
            return _error_result(exc)

    # ====================================================
    # Customer Ticket Proposal
    # ====================================================

    @tool
    def propose_tickets(
        tickets: list[ProposedTicket],
    ):
        """
        Save customer ticket drafts.

        This tool never creates actual tickets.
        """
        if user_role != UserRole.CUSTOMER:
            return {
                "success": False,
                "message": (
                    "Only customers can propose "
                    "their own tickets."
                ),
            }

        if not 1 <= len(tickets) <= 5:
            return {
                "success": False,
                "message": (
                    "Provide between 1 and 5 tickets."
                ),
            }

        try:
            validated = [
                TicketCreate(
                    subject=item.subject,
                    description=item.description,
                ).model_dump(mode="json")
                for item in tickets
            ]

            draft = db.get(
                PendingTicketDraft,
                user_id,
            )

            if draft is None:
                draft = PendingTicketDraft(
                    user_id=user_id,
                    customer_id=None,
                    tickets=validated,
                )

                db.add(draft)

            else:
                draft.customer_id = None
                draft.tickets = validated
                draft.created_at = datetime.now(
                    timezone.utc
                )

            db.commit()

            return {
                "success": True,
                "tickets": validated,
                "tickets_created": 0,
                "message": (
                    "Draft saved; confirmation required."
                ),
            }

        except ValidationError:
            db.rollback()

            return {
                "success": False,
                "message": "Invalid ticket details.",
            }

        except Exception:
            db.rollback()
            raise

    # ====================================================
    # Customer Lookup
    # ====================================================

    @tool
    def find_customer_by_email(email: str):
        """
        Find an active customer by exact email.

        Available only to authenticated agents.
        """
        if user_role != UserRole.AGENT:
            return {
                "success": False,
                "message": (
                    "Only agents can look up customers."
                ),
            }

        customer = (
            db.query(User)
            .filter(
                func.lower(User.email)
                == email.strip().lower(),
                User.role == UserRole.CUSTOMER,
                User.status == UserStatus.ACTIVE,
            )
            .first()
        )

        if customer is None:
            return {
                "success": False,
                "message": "Active customer not found.",
            }

        verified_customer_ids.add(
            customer.id
        )

        return {
            "success": True,
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
            },
        }

    # ====================================================
    # Create Draft on Behalf of Customer
    # ====================================================

    @tool
    def propose_tickets_on_behalf(
        customer_id: int,
        tickets: list[ProposedTicket],
    ):
        """
        Save drafts for a verified customer.

        The agent must confirm before creation.
        """
        if user_role != UserRole.AGENT:
            return {
                "success": False,
                "message": (
                    "Only agents can use this tool."
                ),
            }

        if customer_id not in verified_customer_ids:
            return {
                "success": False,
                "message": (
                    "Verify this customer by email "
                    "before preparing a draft."
                ),
            }

        if not 1 <= len(tickets) <= 5:
            return {
                "success": False,
                "message": (
                    "Provide between 1 and 5 tickets."
                ),
            }

        customer = (
            db.query(User)
            .filter(
                User.id == customer_id,
                User.role == UserRole.CUSTOMER,
                User.status == UserStatus.ACTIVE,
            )
            .first()
        )

        if customer is None:
            return {
                "success": False,
                "message": "Active customer not found.",
            }

        try:
            validated = [
                TicketCreate(
                    subject=item.subject,
                    description=item.description,
                ).model_dump(mode="json")
                for item in tickets
            ]

            draft = db.get(
                PendingTicketDraft,
                user_id,
            )

            if draft is None:
                draft = PendingTicketDraft(
                    user_id=user_id,
                    customer_id=customer.id,
                    tickets=validated,
                )

                db.add(draft)

            else:
                draft.customer_id = customer.id
                draft.tickets = validated
                draft.created_at = datetime.now(
                    timezone.utc
                )

            db.commit()

            return {
                "success": True,
                "customer": {
                    "id": customer.id,
                    "name": customer.name,
                    "email": customer.email,
                },
                "tickets": validated,
                "tickets_created": 0,
                "message": (
                    "Draft saved; agent confirmation required."
                ),
            }

        except ValidationError:
            db.rollback()

            return {
                "success": False,
                "message": "Invalid ticket details.",
            }

        except Exception:
            db.rollback()
            raise

    # ====================================================
    # Check Ticket Status
    # ====================================================

    @tool
    def check_ticket_status(ticket_id: int):
        """Check an accessible ticket's current status."""
        try:
            ticket = ticket_service.get_ticket(
                ticket_id=ticket_id,
                user_id=user_id,
                user_role=user_role,
                db=db,
            )

            return {
                "success": True,
                "ticket_id": ticket.id,
                "status": ticket.status.value,
                "classification_status": (
                    ticket.classification_status
                ),
            }

        except HTTPException as exc:
            return _error_result(exc)

    # ====================================================
    # Update Ticket
    # ====================================================

    @tool
    def update_ticket(
        ticket_id: int,
        priority: str | None = None,
        status: str | None = None,
    ):
        """
        Update ticket priority or status.

        Only authorized agents and admins.
        """
        if user_role not in (
            UserRole.AGENT,
            UserRole.ADMIN,
        ):
            return {
                "success": False,
                "message": (
                    "Only agents and admins "
                    "can update tickets."
                ),
            }

        if priority is None and status is None:
            return {
                "success": False,
                "message": (
                    "Provide a priority or status."
                ),
            }

        try:
            changes = {
                key: value
                for key, value in {
                    "priority": priority,
                    "status": status,
                }.items()
                if value is not None
            }

            ticket_data = TicketUpdate(
                **changes
            )

            ticket = ticket_service.update_ticket(
                ticket_id=ticket_id,
                ticket_data=ticket_data,
                user_id=user_id,
                user_role=user_role,
                db=db,
            )

            return {
                "success": True,
                "message": (
                    "Ticket updated successfully."
                ),
                "ticket": _ticket_to_dict(ticket),
            }

        except ValidationError:
            return {
                "success": False,
                "message": (
                    "Invalid priority or ticket status."
                ),
            }

        except HTTPException as exc:
            return _error_result(exc)

    # ====================================================
    # Escalate Ticket
    # ====================================================

    @tool
    def escalate_ticket(ticket_id: int):
        """
        Escalate an assigned ticket to Critical.

        Requires an explicit agent request.
        """
        if user_role != UserRole.AGENT:
            return {
                "success": False,
                "message": (
                    "Only agents can escalate tickets."
                ),
            }

        try:
            ticket = ticket_service.update_ticket(
                ticket_id=ticket_id,
                ticket_data=TicketUpdate(
                    priority="Critical"
                ),
                user_id=user_id,
                user_role=user_role,
                db=db,
            )

            db.add(
                AuditLog(
                    admin_id=user_id,
                    ticket_id=ticket_id,
                    action="Ticket escalated",
                )
            )

            db.commit()

            return {
                "success": True,
                "message": (
                    "Ticket escalated successfully."
                ),
                "ticket": _ticket_to_dict(ticket),
            }

        except HTTPException as exc:
            db.rollback()
            return _error_result(exc)

        except Exception:
            db.rollback()
            raise

    # ====================================================
    # Role-Specific Tools
    # ====================================================

    common = [
        get_ticket_details,
        check_ticket_status,
    ]

    if user_role == UserRole.CUSTOMER:
        return [
            get_customer_tickets,
            propose_tickets,
            *common,
        ]

    if user_role == UserRole.AGENT:
        return [
            find_customer_by_email,
            propose_tickets_on_behalf,
            *common,
            update_ticket,
            escalate_ticket,
        ]

    if user_role == UserRole.ADMIN:
        return [
            *common,
            update_ticket,
        ]

    return []