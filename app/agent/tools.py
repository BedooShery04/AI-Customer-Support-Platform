

from langchain_core.tools import tool


@tool
def get_customer_tickets(customer_id: int):
    """
    Get the tickets belonging to the current customer.

    Use this tool when the customer asks to view their tickets,
    especially open or active tickets.
    """
    # TODO: Connect this tool to ticket_service
    raise NotImplementedError(
        "get_customer_tickets is not connected to ticket_service yet."
    )


@tool
def get_ticket_details(ticket_id: int):
    """
    Get the details of a specific support ticket.

    Use this tool when the user asks about a specific ticket.
    """
    # TODO: Connect this tool to ticket_service
    raise NotImplementedError(
        "get_ticket_details is not connected to ticket_service yet."
    )


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
    # TODO: Connect this tool to ticket_service
    raise NotImplementedError(
        "create_ticket is not connected to ticket_service yet."
    )


@tool
def check_ticket_status(ticket_id: int):
    """
    Check the current status of a specific support ticket.
    """
    # TODO: Connect this tool to ticket_service
    raise NotImplementedError(
        "check_ticket_status is not connected to ticket_service yet."
    )


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
    """
    # TODO: Connect this tool to ticket_service
    raise NotImplementedError(
        "update_ticket is not connected to ticket_service yet."
    )


@tool
def escalate_ticket(ticket_id: int):
    """
    Escalate a support ticket when escalation is required.
    """
    # TODO: Connect this tool to ticket_service
    raise NotImplementedError(
        "escalate_ticket is not connected to ticket_service yet."
    )


# All tools available to the AI Agent
AGENT_TOOLS = [
    get_customer_tickets,
    get_ticket_details,
    create_ticket,
    check_ticket_status,
    update_ticket,
    escalate_ticket,
]