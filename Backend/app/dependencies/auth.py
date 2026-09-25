from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.services.auth_service import decode_access_token
from app.enums.user import UserStatus


security = HTTPBearer(
    auto_error=False
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
    db: Session = Depends(get_db),
) -> User:

    # =====================================================
    # 1 Check authentication credentials
    # =====================================================

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    # =====================================================
    # 2 Extract JWT
    # =====================================================

    token = credentials.credentials

    # =====================================================
    # 3 Decode and verify JWT
    # =====================================================

    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    # =====================================================
    # 4 Get user ID from JWT
    # =====================================================

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    # =====================================================
    # 5. Convert user ID to integer
    # =====================================================

    try:
        user_id = int(user_id)

    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token.",
        )

    # =====================================================
    # 6 Get user from database
    # =====================================================

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    # =====================================================
    # 7 Check account status
    # =====================================================

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive.",
        )

    # =====================================================
    # 8 Return current user
    # =====================================================

    return user