from fastapi import Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.enums.user import UserRole
from app.models.user import User


# =========================================================
# Admin
# =========================================================

def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Allow access only to Admin users.

    get_current_user() already checks authentication.
    This function only checks the user's role.
    """

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required."
        )

    return current_user


# =========================================================
# Agent
# =========================================================

def require_agent(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Allow access only to Support Agent users.

    get_current_user() already checks authentication.
    This function only checks the user's role.
    """

    if current_user.role != UserRole.AGENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent access required."
        )

    return current_user


# =========================================================
# Customer
# =========================================================

def require_customer(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Allow access only to Customer users.

    get_current_user() already checks authentication.
    This function only checks the user's role.
    """

    if current_user.role != UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access required."
        )

    return current_user