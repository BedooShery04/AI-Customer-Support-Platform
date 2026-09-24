from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.database import get_db

from app.dependencies.auth import get_current_user
from app.dependencies.roles import (
    require_admin,
    require_agent,
    require_customer,
)

from app.models.user import User

from app.schemas.ticket import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
)

from app.services.ticket_service import (
    create_ticket,
    get_all_tickets,
    get_customer_tickets,
    get_agent_tickets,
    get_ticket,
    update_ticket,
    delete_ticket,
)


router = APIRouter(
    prefix="/tickets",
    tags=["Tickets"]
)


# =========================================================
# Create a new ticket
# Customer only
# =========================================================

@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED
)
def create_new_ticket(
    ticket_data: TicketCreate,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    return create_ticket(
        ticket_data=ticket_data,
        user_id=current_user.id,
        user_role=current_user.role,
        db=db
    )


# =========================================================
# Get all tickets
# Admin only
# =========================================================

@router.get(
    "",
    response_model=list[TicketResponse]
)
def get_all(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    return get_all_tickets(
        user_role=current_user.role,
        db=db
    )


# =========================================================
# Get my tickets
# Customer only
# =========================================================

@router.get(
    "/my",
    response_model=list[TicketResponse]
)
def get_my_tickets(
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    return get_customer_tickets(
        customer_id=current_user.id,
        user_id=current_user.id,
        user_role=current_user.role,
        db=db
    )


# =========================================================
# Get my assigned tickets
# Agent only
# =========================================================

@router.get(
    "/assigned",
    response_model=list[TicketResponse]
)
def get_my_assigned_tickets(
    current_user: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    return get_agent_tickets(
        agent_id=current_user.id,
        user_id=current_user.id,
        user_role=current_user.role,
        db=db
    )


# =========================================================
# Get one specific ticket
# Customer / Agent / Admin
# =========================================================

@router.get(
    "/{ticket_id}",
    response_model=TicketResponse
)
def get_single_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_ticket(
        ticket_id=ticket_id,
        user_id=current_user.id,
        user_role=current_user.role,
        db=db
    )


# =========================================================
# Update a ticket
# Agent / Admin
# =========================================================

@router.put(
    "/{ticket_id}",
    response_model=TicketResponse
)
def update_existing_ticket(
    ticket_id: int,
    ticket_data: TicketUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return update_ticket(
        ticket_id=ticket_id,
        ticket_data=ticket_data,
        user_id=current_user.id,
        user_role=current_user.role,
        db=db
    )


# =========================================================
# Delete a ticket
# Admin only
# =========================================================

@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_existing_ticket(
    ticket_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    delete_ticket(
        ticket_id=ticket_id,
        user_role=current_user.role,
        db=db
    )

    return None