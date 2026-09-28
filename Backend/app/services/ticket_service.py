from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.enums import TicketCategory, TicketPriority
from app.enums.user import UserRole, UserStatus
from app.models.audit_log import AuditLog
from app.models.pending_ticket_draft import PendingTicketDraft
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.models.pending_ticket_update import PendingTicketUpdate



DAILY_TICKET_LIMIT = 5
EGYPT_TIMEZONE = ZoneInfo("Africa/Cairo")


# ============================================================
# Helpers
# ============================================================

def get_egypt_day_boundaries() -> tuple[datetime, datetime]:
    """
    Return naive Cairo-local boundaries.

    tickets.created_at is stored as a timezone-naive
    timestamp representing Cairo local time.
    """
    today = datetime.now(EGYPT_TIMEZONE).date()

    start = datetime.combine(
        today,
        datetime.min.time(),
    )

    end = datetime.combine(
        today + timedelta(days=1),
        datetime.min.time(),
    )

    return start, end


def get_ticket_query(db: Session):
    return db.query(Ticket).options(
        joinedload(Ticket.customer),
        joinedload(Ticket.ai_classification),
    )


def _require_active_customer(
    db: Session,
    customer_id: int,
) -> User:
    # Lock the customer to serialize ticket creation.
    customer = (
        db.query(User)
        .filter(User.id == customer_id)
        .with_for_update()
        .first()
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    if (
        customer.role != UserRole.CUSTOMER
        or customer.status != UserStatus.ACTIVE
    ):
        raise HTTPException(
            status_code=400,
            detail="Selected user is not an active customer.",
        )

    return customer


def _require_active_agent(
    db: Session,
    agent_id: int,
) -> User:
    agent = db.get(User, agent_id)

    if (
        agent is None
        or agent.role != UserRole.AGENT
        or agent.status != UserStatus.ACTIVE
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Only active agents can create tickets "
                "on behalf of customers."
            ),
        )

    return agent


def _check_daily_allowance(
    db: Session,
    customer_id: int,
    requested: int,
) -> None:
    start, end = get_egypt_day_boundaries()

    existing = (
        db.query(func.count(Ticket.id))
        .filter(
            Ticket.customer_id == customer_id,
            Ticket.created_at >= start,
            Ticket.created_at < end,
        )
        .scalar()
    ) or 0

    remaining = max(
        0,
        DAILY_TICKET_LIMIT - existing,
    )

    if requested > remaining:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Customer has {remaining} of "
                f"{DAILY_TICKET_LIMIT} daily tickets "
                f"remaining. Requested {requested}; "
                "no tickets were created."
            ),
        )


def _new_ticket(
    db: Session,
    customer_id: int,
    data: TicketCreate,
) -> Ticket:
    ticket = Ticket(
        customer_id=customer_id,
        subject=data.subject,
        description=data.description,
        category=TicketCategory.GENERAL_INQUIRY,
        priority=TicketPriority.MEDIUM,
        classification_status="pending",
        created_at=datetime.now(
            EGYPT_TIMEZONE
        ).replace(tzinfo=None),
    )

    db.add(ticket)
    db.flush()

    return ticket


# ============================================================
# Ticket Retrieval
# ============================================================

def get_all_tickets(
    user_role: UserRole,
    db: Session,
) -> list[Ticket]:
    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only admins can view all tickets.",
        )

    return get_ticket_query(db).all()


def get_customer_tickets(
    customer_id: int,
    user_id: int,
    user_role: UserRole,
    db: Session,
) -> list[Ticket]:
    if (
        user_role != UserRole.CUSTOMER
        or customer_id != user_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You cannot access these tickets.",
        )

    return (
        get_ticket_query(db)
        .filter(Ticket.customer_id == customer_id)
        .order_by(Ticket.created_at.desc())
        .all()
    )


def get_agent_tickets(
    agent_id: int,
    user_id: int,
    user_role: UserRole,
    db: Session,
) -> list[Ticket]:
    if (
        user_role != UserRole.AGENT
        or agent_id != user_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You cannot access these tickets.",
        )

    return (
        get_ticket_query(db)
        .filter(Ticket.assigned_agent_id == agent_id)
        .order_by(Ticket.created_at.desc())
        .all()
    )


def get_ticket(
    ticket_id: int,
    user_id: int,
    user_role: UserRole,
    db: Session,
) -> Ticket:
    ticket = (
        get_ticket_query(db)
        .filter(Ticket.id == ticket_id)
        .first()
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found.",
        )

    if user_role == UserRole.ADMIN:
        return ticket

    if (
        user_role == UserRole.CUSTOMER
        and ticket.customer_id == user_id
    ):
        return ticket

    if (
        user_role == UserRole.AGENT
        and ticket.assigned_agent_id == user_id
    ):
        return ticket

    raise HTTPException(
        status_code=403,
        detail="You cannot access this ticket.",
    )


# ============================================================
# Ticket Creation
# ============================================================

def create_ticket(
    ticket_data: TicketCreate,
    user_id: int,
    user_role: UserRole,
    db: Session,
) -> Ticket:
    if user_role != UserRole.CUSTOMER:
        raise HTTPException(
            status_code=403,
            detail="Only customers can create their own tickets.",
        )

    try:
        _require_active_customer(db, user_id)
        _check_daily_allowance(db, user_id, 1)

        ticket = _new_ticket(
            db,
            user_id,
            ticket_data,
        )

        db.commit()
        db.refresh(ticket)

        return ticket

    except Exception:
        db.rollback()
        raise


def create_ticket_on_behalf(
    ticket_data: TicketCreate,
    customer_id: int,
    agent_id: int,
    db: Session,
) -> Ticket:
    """
    Create a ticket for an active customer.

    The ticket and audit record are committed together.
    """
    try:
        _require_active_agent(db, agent_id)
        _require_active_customer(db, customer_id)
        _check_daily_allowance(db, customer_id, 1)

        ticket = _new_ticket(
            db,
            customer_id,
            ticket_data,
        )

        db.add(
            AuditLog(
                admin_id=agent_id,
                ticket_id=ticket.id,
                action=(
                    "Ticket created on behalf of "
                    f"customer #{customer_id}"
                ),
            )
        )

        db.commit()
        db.refresh(ticket)

        return ticket

    except Exception:
        db.rollback()
        raise


def confirm_ticket_draft(
    db: Session,
    user_id: int,
    user_role: UserRole,
    is_expired,
) -> list[dict]:
    """
    Lock and confirm the entire draft atomically.

    Either all proposed tickets are created,
    or none are created.
    """
    try:
        draft = (
            db.query(PendingTicketDraft)
            .filter(PendingTicketDraft.user_id == user_id)
            .with_for_update()
            .first()
        )

        if draft is None:
            raise HTTPException(
                status_code=404,
                detail="There is no pending ticket draft to confirm.",
            )

        if is_expired(draft):
            db.delete(draft)
            db.commit()

            return []

        if draft.customer_id is None:
            if user_role != UserRole.CUSTOMER:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Only customers can confirm "
                        "their own drafts."
                    ),
                )

            customer_id = user_id
            agent_id = None

        else:
            if user_role != UserRole.AGENT:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Only agents can confirm "
                        "on-behalf drafts."
                    ),
                )

            _require_active_agent(db, user_id)

            customer_id = draft.customer_id
            agent_id = user_id

        _require_active_customer(
            db,
            customer_id,
        )

        proposed = [
            TicketCreate(**item)
            for item in draft.tickets
        ]

        if not 1 <= len(proposed) <= DAILY_TICKET_LIMIT:
            raise HTTPException(
                status_code=422,
                detail=(
                    "A draft must contain "
                    "between 1 and 5 tickets."
                ),
            )

        _check_daily_allowance(
            db,
            customer_id,
            len(proposed),
        )

        created = []

        for data in proposed:
            ticket = _new_ticket(
                db,
                customer_id,
                data,
            )

            if agent_id is not None:
                db.add(
                    AuditLog(
                        admin_id=agent_id,
                        ticket_id=ticket.id,
                        action=(
                            "Ticket created on behalf of "
                            f"customer #{customer_id}"
                        ),
                    )
                )

            created.append({
                "id": ticket.id,
                "subject": ticket.subject,
            })

        db.delete(draft)
        db.commit()

        return created

    except Exception:
        db.rollback()

        raise





def update_customer_ticket(
    ticket_id: int,
    user_id: int,
    user_role: UserRole,
    db: Session,
    subject: str | None = None,
    description: str | None = None,
) -> Ticket:
    if user_role != UserRole.CUSTOMER:
        raise HTTPException(
            status_code=403,
            detail="Only customers can update their own tickets.",
        )

    if subject is None and description is None:
        raise HTTPException(
            status_code=422,
            detail="Provide a subject or description to update.",
        )

    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id)
        .with_for_update()
        .first()
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found.",
        )

    if ticket.customer_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot update another customer's ticket.",
        )

    ticket_status = getattr(ticket.status, "value", ticket.status)

    if ticket_status != "Open":
        raise HTTPException(
            status_code=409,
            detail="Only open tickets can be edited by customers.",
        )

    if subject is not None:
        subject = subject.strip()

        if not 5 <= len(subject) <= 200:
            raise HTTPException(
                status_code=422,
                detail="Subject must contain between 5 and 200 characters.",
            )

        ticket.subject = subject

    if description is not None:
        description = description.strip()

        if not 10 <= len(description) <= 5000:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Description must contain between "
                    "10 and 5000 characters."
                ),
            )

        ticket.description = description

    try:
        db.commit()
        db.refresh(ticket)
        return ticket

    except Exception:
        db.rollback()
        raise




# ============================================================
# Ticket Updates
# ============================================================

def update_ticket(
    ticket_id: int,
    ticket_data: TicketUpdate,
    user_id: int,
    user_role: UserRole,
    db: Session,
) -> Ticket:
    if user_role not in (
        UserRole.AGENT,
        UserRole.ADMIN,
    ):
        raise HTTPException(
            status_code=403,
            detail="You cannot update tickets.",
        )

    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id)
        .first()
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found.",
        )

    if user_role == UserRole.AGENT:
        if ticket.assigned_agent_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="You cannot update this ticket.",
            )

        if "assigned_agent_id" in ticket_data.model_fields_set:
            raise HTTPException(
                status_code=403,
                detail="Agents cannot reassign tickets.",
            )

    changes = ticket_data.model_dump(
        exclude_unset=True
    )

    changes.pop("assigned_agent_id", None)

    for field, value in changes.items():
        if value is not None:
            setattr(ticket, field, value)

    if (
        user_role == UserRole.ADMIN
        and "assigned_agent_id" in ticket_data.model_fields_set
    ):
        agent_id = ticket_data.assigned_agent_id

        if agent_id is None:
            ticket.assigned_agent_id = None

        else:
            agent = db.get(User, agent_id)

            if agent is None:
                raise HTTPException(
                    status_code=404,
                    detail="Agent not found.",
                )

            if agent.role != UserRole.AGENT:
                raise HTTPException(
                    status_code=400,
                    detail="Selected user is not an agent.",
                )

            if agent.status != UserStatus.ACTIVE:
                raise HTTPException(
                    status_code=400,
                    detail="Selected agent is not active.",
                )

            ticket.assigned_agent_id = agent.id

    db.commit()
    db.refresh(ticket)

    return ticket


# ============================================================
# Ticket Deletion
# ============================================================

def delete_ticket(
    ticket_id: int,
    user_role: UserRole,
    db: Session,
) -> None:
    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only admins can delete tickets.",
        )

    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id)
        .first()
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found.",
        )

    db.delete(ticket)
    db.commit()







def confirm_customer_ticket_update(
    db: Session,
    user_id: int,
    user_role: UserRole,
    is_expired,
) -> Ticket:
    if user_role != UserRole.CUSTOMER:
        raise HTTPException(
            status_code=403,
            detail="Only customers can confirm ticket edits.",
        )

    try:
        draft = (
            db.query(PendingTicketUpdate)
            .filter(PendingTicketUpdate.user_id == user_id)
            .with_for_update()
            .first()
        )

        if draft is None:
            raise HTTPException(
                status_code=404,
                detail="There is no pending ticket edit.",
            )

        if is_expired(draft):
            db.delete(draft)
            db.commit()

            raise HTTPException(
                status_code=410,
                detail="Your ticket edit draft has expired.",
            )

        customer = db.get(User, user_id)

        if (
            customer is None
            or customer.role != UserRole.CUSTOMER
            or customer.status != UserStatus.ACTIVE
        ):
            raise HTTPException(
                status_code=403,
                detail="Your account cannot edit tickets.",
            )

        ticket = (
            db.query(Ticket)
            .filter(Ticket.id == draft.ticket_id)
            .with_for_update()
            .first()
        )

        if ticket is None:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found.",
            )

        if ticket.customer_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="You cannot edit this ticket.",
            )

        current_status = getattr(
            ticket.status, "value", ticket.status
        )

        if current_status != "Open":
            raise HTTPException(
                status_code=409,
                detail="Only open tickets can be edited.",
            )

        if draft.subject is not None:
            subject = draft.subject.strip()

            if not 5 <= len(subject) <= 200:
                raise HTTPException(
                    status_code=422,
                    detail="Invalid ticket subject.",
                )

            ticket.subject = subject

        if draft.description is not None:
            description = draft.description.strip()

            if not 10 <= len(description) <= 5000:
                raise HTTPException(
                    status_code=422,
                    detail="Invalid ticket description.",
                )

            ticket.description = description

        db.delete(draft)
        db.commit()
        db.refresh(ticket)

        return ticket

    except HTTPException as exc:
        if exc.status_code != 410:
            db.rollback()
        raise

    except Exception:
        db.rollback()
        raise