
from datetime import datetime, timezone

from fastapi import HTTPException
from langchain_core.tools import tool
from app.schemas.proposed_ticket import ProposedTicket
from pydantic import  ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.enums import UserRole
from app.enums.user import UserStatus
from app.models.audit_log import AuditLog
from app.models.pending_ticket_draft import PendingTicketDraft
from app.models.pending_ticket_update import PendingTicketUpdate
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.services import ticket_service




def _ticket_to_dict(
    ticket,
    include_priority: bool = True,
):
    """
    Convert a ticket to a dictionary.

    Priority is hidden from customer-facing AI tools.
    """
    data = {
        "id": ticket.id,
        "customer_id": ticket.customer_id,
        "assigned_agent_id": ticket.assigned_agent_id,
        "subject": ticket.subject,
        "description": ticket.description,
        "category": ticket.category.value,
        "status": ticket.status.value,
        "classification_status": ticket.classification_status,
        "created_at": (
            ticket.created_at.isoformat()
            if ticket.created_at
            else None
        ),
        "updated_at": (
            ticket.updated_at.isoformat()
            if ticket.updated_at
            else None
        ),
    }

    if include_priority:
        data["priority"] = ticket.priority.value

    return data


def _error_result(exc: HTTPException):
    return {
        "success": False,
        "status_code": exc.status_code,
        "message": str(exc.detail),
    }


def build_tools(
    db: Session,
    user_id: int,
    chat_id: int,
    user_role: UserRole,
):
    """
    Build tools according to the authenticated user's role.

    The user ID, chat ID and role are supplied by the
    backend and must never come from the AI model.
    """

    # ====================================================
    # Customer Tickets
    # ====================================================

    @tool
    def get_customer_tickets():
        """
        Retrieve all tickets owned by the authenticated
        customer. Use this tool when a customer identifies
        a ticket by its subject instead of its ID.
        """
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
                    _ticket_to_dict(
                        ticket,
                        include_priority=False,
                    )
                    for ticket in tickets
                ],
            }

        except HTTPException as exc:
            db.rollback()
            return _error_result(exc)

    # ====================================================
    # Ticket Details
    # ====================================================

    @tool
    def get_ticket_details(ticket_id: int):
        """
        Retrieve an accessible ticket's details.

        Customers can retrieve only their own tickets.
        Agents and admins follow backend access rules.
        """
        try:
            ticket = ticket_service.get_ticket(
                ticket_id=ticket_id,
                user_id=user_id,
                user_role=user_role,
                db=db,
            )

            return {
                "success": True,
                "ticket": _ticket_to_dict(
                    ticket,
                    include_priority=(
                        user_role != UserRole.CUSTOMER
                    ),
                ),
            }

        except HTTPException as exc:
            db.rollback()
            return _error_result(exc)

    # ====================================================
    # Customer Ticket Proposal
    # ====================================================

    @tool
    def propose_tickets(
        tickets: list[ProposedTicket],
    ):
        """
        Save customer ticket creation drafts in this chat.

        This tool never creates actual tickets.
        Backend confirmation is required.
        """
        if user_role != UserRole.CUSTOMER:
            return {
                "success": False,
                "status_code": 403,
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
            # Prevent conflicting operations in this chat.
            if db.get(
                PendingTicketUpdate,
                (user_id, chat_id),
            ) is not None:
                return {
                    "success": False,
                    "message": (
                        "Please confirm or cancel your "
                        "pending ticket edit first."
                    ),
                }

            validated = [
                TicketCreate(
                    subject=item.subject,
                    description=item.description,
                ).model_dump(mode="json")
                for item in tickets
            ]

            # Find the creation draft for this chat only.
            draft = db.get(
                PendingTicketDraft,
                (user_id, chat_id),
            )

            if draft is None:
                draft = PendingTicketDraft(
                    user_id=user_id,
                    chat_id=chat_id,
                    customer_id=None,
                    tickets=validated,
                    created_at=datetime.now(timezone.utc),
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
                "status_code": 403,
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
        customer_email: str,
        tickets: list[ProposedTicket],
    ):
        """
        Save ticket creation drafts for an active customer
        in the agent's currently selected chat.

        Verify the customer's exact email before saving.
        Actual ticket creation requires explicit agent
        confirmation.
        """
        if user_role != UserRole.AGENT:
            return {
                "success": False,
                "status_code": 403,
                "message": "Only agents can use this tool.",
            }

        if not 1 <= len(tickets) <= 5:
            return {
                "success": False,
                "message": "Provide between 1 and 5 tickets.",
            }

        email = customer_email.strip().lower()

        if not email:
            return {
                "success": False,
                "message": "Customer email is required.",
            }

        try:
            agent = db.get(User, user_id)

            if (
                agent is None
                or agent.role != UserRole.AGENT
                or agent.status != UserStatus.ACTIVE
            ):
                return {
                    "success": False,
                    "status_code": 403,
                    "message": (
                        "Only active agents can create drafts."
                    ),
                }

            customer = (
                db.query(User)
                .filter(
                    func.lower(User.email) == email,
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

            # Check only the selected chat.
            if db.get(
                PendingTicketUpdate,
                (user_id, chat_id),
            ) is not None:
                return {
                    "success": False,
                    "message": (
                        "Please confirm or cancel the pending "
                        "ticket edit before creating a new draft."
                    ),
                }

            validated = [
                TicketCreate(
                    subject=item.subject,
                    description=item.description,
                ).model_dump(mode="json")
                for item in tickets
            ]

            draft = db.get(
                PendingTicketDraft,
                (user_id, chat_id),
            )

            if draft is None:
                draft = PendingTicketDraft(
                    user_id=user_id,
                    chat_id=chat_id,
                    customer_id=customer.id,
                    tickets=validated,
                    created_at=datetime.now(timezone.utc),
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
                    "Draft saved successfully. "
                    "Explicit agent confirmation is required."
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
        """
        Check an accessible ticket's current status.
        """
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
            db.rollback()
            return _error_result(exc)

    # ====================================================
    # Staff Ticket Update
    # ====================================================

    @tool
    def update_ticket(
        ticket_id: int,
        priority: str | None = None,
        status: str | None = None,
    ):
        """
        Update ticket priority or status.

        Only authorized agents and admins can
        perform these operations.
        """
        if user_role not in (
            UserRole.AGENT,
            UserRole.ADMIN,
        ):
            return {
                "success": False,
                "status_code": 403,
                "message": (
                    "Only agents and admins "
                    "can update ticket priority or status."
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
            db.rollback()

            return {
                "success": False,
                "message": (
                    "Invalid priority or ticket status."
                ),
            }

        except HTTPException as exc:
            db.rollback()
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
                "status_code": 403,
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
    # Customer Ticket Edit Proposal
    # ====================================================

    @tool
    def propose_ticket_update(
        ticket_id: int,
        subject: str | None = None,
        description: str | None = None,
    ):
        """
        Prepare changes to the authenticated customer's
        own open ticket in the currently selected chat.

        Never apply changes directly.
        Save a draft and require backend confirmation.

        When revising a pending draft for the same ticket,
        omitted fields retain their previously proposed
        values.
        """
        if user_role != UserRole.CUSTOMER:
            return {
                "success": False,
                "status_code": 403,
                "message": (
                    "Only customers can edit "
                    "their own tickets."
                ),
            }

        if subject is None and description is None:
            return {
                "success": False,
                "message": (
                    "Provide a subject or description."
                ),
            }

        try:
            ticket = ticket_service.get_ticket(
                ticket_id=ticket_id,
                user_id=user_id,
                user_role=user_role,
                db=db,
            )

            current_status = getattr(
                ticket.status,
                "value",
                ticket.status,
            )

            if str(current_status).casefold() != "open":
                return {
                    "success": False,
                    "status_code": 409,
                    "message": (
                        "Only open tickets can be edited."
                    ),
                }

            # Prevent conflicting operations in this chat.
            if db.get(
                PendingTicketDraft,
                (user_id, chat_id),
            ) is not None:
                return {
                    "success": False,
                    "message": (
                        "Please confirm or cancel your "
                        "pending ticket creation first."
                    ),
                }

            draft = db.get(
                PendingTicketUpdate,
                (user_id, chat_id),
            )

            # Allow revisions to the same ticket only.
            if (
                draft is not None
                and draft.ticket_id != ticket.id
            ):
                return {
                    "success": False,
                    "message": (
                        "You already have a pending edit "
                        f"for ticket #{draft.ticket_id}. "
                        "Please confirm or cancel it first."
                    ),
                }

            # Preserve previously proposed fields.
            new_subject = (
                subject
                if subject is not None
                else (
                    draft.subject
                    if draft is not None
                    else None
                )
            )

            new_description = (
                description
                if description is not None
                else (
                    draft.description
                    if draft is not None
                    else None
                )
            )

            if new_subject is not None:
                new_subject = new_subject.strip()

                if not 5 <= len(new_subject) <= 200:
                    return {
                        "success": False,
                        "message": (
                            "Subject must be "
                            "5-200 characters."
                        ),
                    }

            if new_description is not None:
                new_description = new_description.strip()

                if not 10 <= len(new_description) <= 5000:
                    return {
                        "success": False,
                        "message": (
                            "Description must be "
                            "10-5000 characters."
                        ),
                    }

            # Create or revise the draft in this chat.
            if draft is None:
                draft = PendingTicketUpdate(
                    user_id=user_id,
                    chat_id=chat_id,
                    ticket_id=ticket.id,
                    subject=new_subject,
                    description=new_description,
                    created_at=datetime.now(
                        timezone.utc
                    ),
                )

                db.add(draft)

            else:
                draft.subject = new_subject
                draft.description = new_description
                draft.created_at = datetime.now(
                    timezone.utc
                )

            db.commit()

            return {
                "success": True,
                "message": (
                    "Ticket edit draft saved. "
                    "Customer confirmation is required."
                ),
                "ticket_id": ticket.id,
                "old_subject": ticket.subject,
                "old_description": ticket.description,
                "new_subject": new_subject,
                "new_description": new_description,
                "changes_applied": False,
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
            propose_ticket_update,
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