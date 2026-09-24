from fastapi import Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.enums.user import UserRole
from app.models.user import User


def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required."
        )

    return current_user


def require_agent(
    current_user: User = Depends(get_current_user)
) -> User:

    if current_user.role != UserRole.AGENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent access required."
        )

    return current_user