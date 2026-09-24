from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.enums import UserRole
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate, TicketUpdate


# =========================================================
# Get all tickets
# =========================================================

def get_all_tickets(db: Session):
    tickets = db.query(Ticket).all()
    return tickets


# =========================================================
# Get customer's tickets
# =========================================================

def get_customer_tickets(
    customer_id: int,
    db: Session
):
    tickets = (
        db.query(Ticket)
        .filter(Ticket.customer_id == customer_id)
        .all()
    )

    return tickets


# =========================================================
# Get agent's assigned tickets
# =========================================================

def get_agent_tickets(
    agent_id: int,
    db: Session
):
    tickets = (
        db.query(Ticket)
        .filter(Ticket.assigned_agent_id == agent_id)
        .all()
    )

    return tickets


# =========================================================
# Get specific ticket
# =========================================================

def get_ticket(
    ticket_id: int,
    user_id: int,
    user_role: UserRole,
    db: Session
):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id)
        .first()
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    # Admin can view any ticket
    if user_role == UserRole.ADMIN:
        return ticket

    # Customer can view only their own tickets
    if user_role == UserRole.CUSTOMER:
        if ticket.customer_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to access this ticket"
            )

        return ticket

    # Agent can view only assigned tickets
    if user_role == UserRole.AGENT:
        if ticket.assigned_agent_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to access this ticket"
            )

        return ticket

    raise HTTPException(
        status_code=403,
        detail="You are not allowed to access tickets"
    )


# =========================================================
# Create a new ticket
# =========================================================

def create_ticket(
    ticket_data: TicketCreate,
    customer_id: int,
    db: Session
):
    new_ticket = Ticket(
        customer_id=customer_id,
        subject=ticket_data.subject,
        description=ticket_data.description,
        category=ticket_data.category,
        priority=ticket_data.priority
    )

    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)

    return new_ticket


# =========================================================
# Update ticket
# =========================================================

def update_ticket(
    ticket_id: int,
    ticket_data: TicketUpdate,
    user_id: int,
    user_role: UserRole,
    db: Session
):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id)
        .first()
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    # Only Agent and Admin can update tickets
    if user_role not in (
        UserRole.AGENT,
        UserRole.ADMIN
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to update tickets"
        )

    # Agent can update only assigned tickets
    if (
        user_role == UserRole.AGENT
        and ticket.assigned_agent_id != user_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to update this ticket"
        )

    if ticket_data.subject is not None:
        ticket.subject = ticket_data.subject

    if ticket_data.description is not None:
        ticket.description = ticket_data.description

    if ticket_data.category is not None:
        ticket.category = ticket_data.category

    if ticket_data.priority is not None:
        ticket.priority = ticket_data.priority

    if ticket_data.status is not None:
        ticket.status = ticket_data.status

    if ticket_data.assigned_agent_id is not None:

        # Assignment is handled by authorized users.
        ticket.assigned_agent_id = (
            ticket_data.assigned_agent_id
        )

    db.commit()
    db.refresh(ticket)

    return ticket


# =========================================================
# Delete ticket
# =========================================================

def delete_ticket(
    ticket_id: int,
    user_role: UserRole,
    db: Session
):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id)
        .first()
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    # Only Admin can delete tickets
    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only admins can delete tickets"
        )

    db.delete(ticket)
    db.commit()