from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.roles import require_admin

from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.models.ticket import Ticket, TicketStatus, TicketPriority
from app.models.ai_classification import TicketAIClassification
from app.models.ai_chat_message import AIChatMessage

from app.schemas.admin_dashboard import AdminDashboardResponse


router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@router.get(
    "/dashboard",
    response_model=AdminDashboardResponse
)
def get_admin_dashboard(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # =========================================================
    # Ticket statistics
    # =========================================================

    total = db.query(Ticket).count()

    open_count = (
        db.query(Ticket)
        .filter(Ticket.status == TicketStatus.OPEN)
        .count()
    )

    in_progress = (
        db.query(Ticket)
        .filter(Ticket.status == TicketStatus.IN_PROGRESS)
        .count()
    )

    resolved = (
        db.query(Ticket)
        .filter(Ticket.status == TicketStatus.RESOLVED)
        .count()
    )

    critical = (
        db.query(Ticket)
        .filter(Ticket.priority == TicketPriority.CRITICAL)
        .count()
    )

    # =========================================================
    # Recent tickets
    # =========================================================

    recent_tickets = (
        db.query(Ticket)
        .order_by(Ticket.created_at.desc())
        .limit(5)
        .all()
    )

    # =========================================================
    # All tickets for statistics
    # =========================================================

    all_tickets = db.query(Ticket).all()

    # ---------------------------------------------------------
    # Tickets by category
    # ---------------------------------------------------------

    tickets_by_category = {}

    for ticket in all_tickets:
        category = ticket.category.value

        tickets_by_category[category] = (
            tickets_by_category.get(category, 0) + 1
        )

    # ---------------------------------------------------------
    # Tickets by status
    # ---------------------------------------------------------

    tickets_by_status = {}

    for ticket in all_tickets:
        status = ticket.status.value

        tickets_by_status[status] = (
            tickets_by_status.get(status, 0) + 1
        )

    # ---------------------------------------------------------
    # Tickets by agent
    # ---------------------------------------------------------

    tickets_by_agent = {}

    for ticket in all_tickets:
        agent_id = (
            str(ticket.assigned_agent_id)
            if ticket.assigned_agent_id is not None
            else "Unassigned"
        )

        tickets_by_agent[agent_id] = (
            tickets_by_agent.get(agent_id, 0) + 1
        )

    # ---------------------------------------------------------
    # Average tickets per category
    # ---------------------------------------------------------

    category_count = len(tickets_by_category)

    average_tickets_per_category = (
        len(all_tickets) / category_count
        if category_count
        else 0
    )

    # =========================================================
    # Support activity
    # =========================================================

    support_rows = (
        db.query(
            User.id,
            User.name,
            func.count(Ticket.id),
        )
        .join(
            Ticket,
            Ticket.assigned_agent_id == User.id,
            isouter=True,
        )
        .filter(User.role == UserRole.AGENT)
        .group_by(User.id, User.name)
        .all()
    )

    support_activity = [
        {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "assigned_tickets": assigned_tickets,
        }
        for agent_id, agent_name, assigned_tickets in support_rows
    ]

    # =========================================================
    # AI activity
    # =========================================================

    # Tickets classified by AI
    classified_tickets = (
        db.query(TicketAIClassification)
        .count()
    )

    # Completed AI chat requests
    chat_requests = (
        db.query(AIChatMessage)
        .filter(AIChatMessage.role == "assistant")
        .count()
    )

    # AI response suggestions generated
    suggestions = (
        db.query(AuditLog)
        .filter(
            AuditLog.action == "AI response suggestion generated"
        )
        .count()
    )

    # =========================================================
    # Response
    # =========================================================

    return {
        "total": total,
        "open": open_count,
        "in_progress": in_progress,
        "resolved": resolved,
        "critical": critical,

        "recent_tickets": recent_tickets,

        "tickets_by_category": tickets_by_category,
        "tickets_by_status": tickets_by_status,
        "tickets_by_agent": tickets_by_agent,
        "average_tickets_per_category": average_tickets_per_category,

        "support_activity": support_activity,

        "ai_activity": {
            "classified_tickets": classified_tickets,
            "chat_requests": chat_requests,
            "suggestions": suggestions,
        },
    }