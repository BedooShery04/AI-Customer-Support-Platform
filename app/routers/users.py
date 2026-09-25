from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_admin
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import (
    get_user_by_id,
    get_user_by_email,
    get_users,
    update_user,
    delete_user,
)


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


# =========================================================
# Get all users
# Admin only
# =========================================================

@router.get(
    "",
    response_model=list[UserResponse]
)
def get_all_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    return get_users(db)


# =========================================================
# Get one user
# Authenticated users
# =========================================================

@router.get(
    "/{user_id}",
    response_model=UserResponse
)
def get_single_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # User can see their own profile
    # Admin can see any user
    if (
        current_user.id != user_id
        and current_user.role.value != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to access this user."
        )

    user = get_user_by_id(
        db=db,
        user_id=user_id
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    return user


# =========================================================
# Update user
# Admin only
# =========================================================

@router.put(
    "/{user_id}",
    response_model=UserResponse
)
def update_existing_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = get_user_by_id(
        db=db,
        user_id=user_id
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # Check duplicate email
    if user_data.email is not None:
        if (
            user.email != user_data.email
            and get_user_by_email(db, user_data.email)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists."
            )

    return update_user(
        db=db,
        user=user,
        name=user_data.name,
        email=user_data.email,
        role=user_data.role,
        status=user_data.status
    )


# =========================================================
# Delete user
# Admin only
# =========================================================

@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_existing_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = get_user_by_id(
        db=db,
        user_id=user_id
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # Prevent admin from deleting himself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account."
        )

    delete_user(
        db=db,
        user=user
    )

    return None