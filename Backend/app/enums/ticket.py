from enum import Enum


class TicketCategory(str, Enum):
    TECHNICAL_ISSUE = "Technical Issue"
    ACCOUNT_ISSUE = "Account Issue"
    BILLING = "Billing"
    PRODUCT_ISSUE = "Product Issue"
    GENERAL_INQUIRY = "General Inquiry"


class TicketPriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class TicketStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    WAITING_FOR_CUSTOMER = "Waiting for Customer"
    RESOLVED = "Resolved"
    CLOSED = "Closed"