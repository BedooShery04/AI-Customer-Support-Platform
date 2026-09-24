from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.enums.user import UserRole, UserStatus
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate, TicketUpdate


# =========================================================
# Get all tickets
# Admin only
# =========================================================

def get_all_tickets(
    user_role: UserRole,
    db: Session
):
    """
    Get all tickets.

    Only Admins are allowed to view all tickets.
    """

    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only admins can view all tickets"
        )

    tickets = db.query(Ticket).all()

    return tickets


# =========================================================
# Get customer's tickets
# Customer only
# =========================================================

def get_customer_tickets(
    customer_id: int,
    user_id: int,
    user_role: UserRole,
    db: Session
):
    """
    Get tickets belonging to the current customer.
    """

    if user_role != UserRole.CUSTOMER:
        raise HTTPException(
            status_code=403,
            detail="Only customers can access customer tickets"
        )

    # Make sure the requested customer_id
    # belongs to the logged-in customer.
    if customer_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to access these tickets"
        )

    tickets = (
        db.query(Ticket)
        .filter(Ticket.customer_id == customer_id)
        .all()
    )

    return tickets


# =========================================================
# Get agent's assigned tickets
# Agent only
# =========================================================

def get_agent_tickets(
    agent_id: int,
    user_id: int,
    user_role: UserRole,
    db: Session
):
    """
    Get tickets assigned to the current support agent.
    """

    if user_role != UserRole.AGENT:
        raise HTTPException(
            status_code=403,
            detail="Only agents can access assigned tickets"
        )

    # Make sure the requested agent_id
    # belongs to the logged-in agent.
    if agent_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to access these tickets"
        )

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
    """
    Get one specific ticket according to the user's role.
    """

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

    # -----------------------------------------------------
    # Admin
    # -----------------------------------------------------

    if user_role == UserRole.ADMIN:
        return ticket

    # -----------------------------------------------------
    # Customer
    # -----------------------------------------------------

    if user_role == UserRole.CUSTOMER:

        if ticket.customer_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to access this ticket"
            )

        return ticket

    # -----------------------------------------------------
    # Agent
    # -----------------------------------------------------

    if user_role == UserRole.AGENT:

        if ticket.assigned_agent_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to access this ticket"
            )

        return ticket

    # -----------------------------------------------------
    # Unknown role
    # -----------------------------------------------------

    raise HTTPException(
        status_code=403,
        detail="You are not allowed to access tickets"
    )


# =========================================================
# Create a new ticket
# Customer only
# =========================================================

def create_ticket(
    ticket_data: TicketCreate,
    user_id: int,
    user_role: UserRole,
    db: Session
):
    """
    Create a new ticket for the current customer.
    """

    if user_role != UserRole.CUSTOMER:
        raise HTTPException(
            status_code=403,
            detail="Only customers can create tickets"
        )

    new_ticket = Ticket(
        customer_id=user_id,
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
# Agent and Admin
# =========================================================

def update_ticket(
    ticket_id: int,
    ticket_data: TicketUpdate,
    user_id: int,
    user_role: UserRole,
    db: Session
):
    """
    Update a ticket.

    Admin:
        Can update any ticket.
        Can assign/reassign the ticket to an agent.

    Agent:
        Can update only tickets assigned to them.
        Cannot change the assigned agent.

    Customer:
        Cannot update tickets.
    """

    # -----------------------------------------------------
    # 1. Get ticket
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # 2. Check role
    # -----------------------------------------------------

    if user_role == UserRole.CUSTOMER:
        raise HTTPException(
            status_code=403,
            detail="Customers are not allowed to update tickets"
        )

    if user_role not in (
        UserRole.AGENT,
        UserRole.ADMIN
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to update tickets"
        )

    # -----------------------------------------------------
    # 3. Agent permission
    # -----------------------------------------------------

    if user_role == UserRole.AGENT:

        # Agent can only update tickets assigned to them
        if ticket.assigned_agent_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to update this ticket"
            )

        # Agent cannot assign/reassign tickets
        if ticket_data.assigned_agent_id is not None:
            raise HTTPException(
                status_code=403,
                detail="Agents cannot assign or reassign tickets"
            )

    # -----------------------------------------------------
    # 4. Update common fields
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # 5. Admin-only assignment
    # -----------------------------------------------------

    if user_role == UserRole.ADMIN:
        if ticket_data.assigned_agent_id is not None:

            agent = (
                db.query(User)
                .filter(User.id == ticket_data.assigned_agent_id)
                .first()
            )

            if agent is None:
                raise HTTPException(
                    status_code=404,
                    detail="Agent not found"
                )

            if agent.role != UserRole.AGENT:
                raise HTTPException(
                    status_code=400,
                    detail="Selected user is not an agent"
                )

            if agent.status != UserStatus.ACTIVE:
                raise HTTPException(
                    status_code=400,
                    detail="Selected agent is inactive"
                )

            ticket.assigned_agent_id = agent.id

    # -----------------------------------------------------
    # 6. Save changes
    # -----------------------------------------------------

    db.commit()
    db.refresh(ticket)

    return ticket


# =========================================================
# Delete ticket
# Admin only
# =========================================================

def delete_ticket(
    ticket_id: int,
    user_role: UserRole,
    db: Session
):
    """
    Delete a ticket.

    Only Admins are allowed to delete tickets.
    """

    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only admins can delete tickets"
        )

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

    db.delete(ticket)
    db.commit()