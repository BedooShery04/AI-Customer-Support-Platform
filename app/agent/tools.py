from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.schemas.ticket import TicketCreate, TicketUpdate
from app.services import ticket_service


def _ticket_to_dict(ticket):
    """
    Convert a Ticket model object into a simple dictionary
    that can be returned to the AI Agent.
    """
    return {
        "id": ticket.id,
        "customer_id": ticket.customer_id,
        "assigned_agent_id": ticket.assigned_agent_id,
        "subject": ticket.subject,
        "description": ticket.description,
        "category": ticket.category.value,
        "priority": ticket.priority.value,
        "status": ticket.status.value,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
    }


def build_tools(db: Session, customer_id: int):
    """
    Build the tools available to the AI Agent.

    customer_id comes from the authenticated user,
    not from the LLM.
    """

    @tool
    def get_customer_tickets():
        """
        Get the tickets belonging to the current customer.

        Use this tool when the customer asks to view their tickets,
        especially open or active tickets.
        """
        tickets = ticket_service.get_customer_tickets(
            customer_id,
            db
        )

        return {
            "success": True,
            "tickets": [_ticket_to_dict(ticket) for ticket in tickets]
        }

    @tool
    def get_ticket_details(ticket_id: int):
        """
        Get the details of a specific support ticket.

        Use this tool when the user asks about a specific ticket.
        """
        ticket = ticket_service.get_ticket(
            ticket_id,
            db
        )

        return {
            "success": True,
            "ticket": _ticket_to_dict(ticket)
        }

    @tool
    def create_ticket(
        subject: str,
        description: str,
        category: str,
        priority: str = "Medium",
    ):
        """
        Create a new support ticket.

        Only use this tool when the user explicitly asks to create a ticket.
        """

        ticket_data = TicketCreate(
            subject=subject,
            description=description,
            category=category,
            priority=priority,
        )

        ticket = ticket_service.create_ticket(
            ticket_data,
            customer_id,
            db
        )

        return {
            "success": True,
            "message": "Ticket created successfully.",
            "ticket": _ticket_to_dict(ticket)
        }

    @tool
    def check_ticket_status(ticket_id: int):
        """
        Check the current status of a specific support ticket.
        """
        ticket = ticket_service.get_ticket(
            ticket_id,
            db
        )

        return {
            "success": True,
            "ticket_id": ticket.id,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
        }

    @tool
    def update_ticket(
        ticket_id: int,
        priority: str | None = None,
        status: str | None = None,
    ):
        """
        Update permitted information for a support ticket.

        Allowed updates currently include priority and status.
        Authorization must be checked by the backend service.
        Only use this tool when the user explicitly requests an update.
        """

        ticket_data = TicketUpdate(
            priority=priority,
            status=status,
        )

        ticket = ticket_service.update_ticket(
            ticket_id,
            ticket_data,
            db
        )

        return {
            "success": True,
            "message": "Ticket updated successfully.",
            "ticket": _ticket_to_dict(ticket)
        }

    @tool
    def escalate_ticket(ticket_id: int):
        """
        Escalate a support ticket when escalation is required.

        Escalation is handled by changing the ticket priority to Critical.
        """

        ticket_data = TicketUpdate(
            priority="Critical"
        )

        ticket = ticket_service.update_ticket(
            ticket_id,
            ticket_data,
            db
        )

        return {
            "success": True,
            "message": "Ticket escalated successfully.",
            "ticket": _ticket_to_dict(ticket)
        }

    return [
        get_customer_tickets,
        get_ticket_details,
        create_ticket,
        check_ticket_status,
        update_ticket,
        escalate_ticket,
    ]