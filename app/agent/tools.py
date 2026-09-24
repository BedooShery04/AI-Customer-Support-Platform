from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.enums import UserRole
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.services import ticket_service


def _ticket_to_dict(ticket):
    """
    Convert a Ticket object into a dictionary
    that the AI can understand.
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


def build_tools(
    db: Session,
    user_id: int,
    user_role: UserRole
):
    """
    Build the tools for the current authenticated user.
    """

    # =========================================================
    # 1 Get Customer Tickets
    # =========================================================

    @tool
    def get_customer_tickets():
        """
        Get the tickets belonging to the current customer.
        """

        if user_role != UserRole.CUSTOMER:
            return {
                "success": False,
                "message": "This tool is only available to customers."
            }

        tickets = ticket_service.get_customer_tickets(
            customer_id=user_id,
            user_id=user_id,
            user_role=user_role,
            db=db
        )

        return {
            "success": True,
            "tickets": [
                _ticket_to_dict(ticket)
                for ticket in tickets
            ]
        }

    # =========================================================
    # 2 Get Ticket Details
    # =========================================================

    @tool
    def get_ticket_details(ticket_id: int):
        """
        Get details of a specific ticket.
        """

        ticket = ticket_service.get_ticket(
            ticket_id=ticket_id,
            user_id=user_id,
            user_role=user_role,
            db=db
        )

        return {
            "success": True,
            "ticket": _ticket_to_dict(ticket)
        }

    # =========================================================
    # 3 Create Ticket
    # =========================================================

    @tool
    def create_ticket(
        subject: str,
        description: str,
        category: str,
        priority: str = "Medium"
    ):
        """
        Create a new support ticket.
        """

        if user_role != UserRole.CUSTOMER:
            return {
                "success": False,
                "message": "Only customers can create tickets."
            }

        ticket_data = TicketCreate(
            subject=subject,
            description=description,
            category=category,
            priority=priority
        )

        ticket = ticket_service.create_ticket(
            ticket_data=ticket_data,
            user_id=user_id,
            user_role=user_role,
            db=db
        )

        return {
            "success": True,
            "message": "Ticket created successfully.",
            "ticket": _ticket_to_dict(ticket)
        }

    # =========================================================
    # 4 Check Ticket Status
    # =========================================================

    @tool
    def check_ticket_status(ticket_id: int):
        """
        Check the current status of a ticket.
        """

        ticket = ticket_service.get_ticket(
            ticket_id=ticket_id,
            user_id=user_id,
            user_role=user_role,
            db=db
        )

        return {
            "success": True,
            "ticket_id": ticket.id,
            "status": ticket.status.value,
            "priority": ticket.priority.value
        }

    # =========================================================
    # 5 Update Ticket
    # =========================================================

    @tool
    def update_ticket(
        ticket_id: int,
        priority: str | None = None,
        status: str | None = None
    ):
        """
        Update ticket priority or status.
        """

        ticket_data = TicketUpdate(
            priority=priority,
            status=status
        )

        ticket = ticket_service.update_ticket(
            ticket_id=ticket_id,
            ticket_data=ticket_data,
            user_id=user_id,
            user_role=user_role,
            db=db
        )

        return {
            "success": True,
            "message": "Ticket updated successfully.",
            "ticket": _ticket_to_dict(ticket)
        }

    # =========================================================
    # 6. Escalate Ticket
    # =========================================================

    @tool
    def escalate_ticket(ticket_id: int):
        """
        Escalate a ticket by changing its priority to Critical.
        """

        ticket_data = TicketUpdate(
            priority="Critical"
        )

        ticket = ticket_service.update_ticket(
            ticket_id=ticket_id,
            ticket_data=ticket_data,
            user_id=user_id,
            user_role=user_role,
            db=db
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
        escalate_ticket
    ]