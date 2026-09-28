
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_admin
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import (
    delete_user,
    get_user_by_id,
    get_users,
    update_user,
)


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


# ============================================================
# User Retrieval
# ============================================================

@router.get(
    "",
    response_model=list[UserResponse],
)
def get_all_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Retrieve all registered users.

    Access:
        Admin only.
    """
    return get_users(db)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
def get_single_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve a user's profile.

    Access:
        Users can view their own profile.
        Admins can view any user's profile.
    """
    if (
        current_user.id != user_id
        and current_user.role.value != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to access this user.",
        )

    user = get_user_by_id(
        db=db,
        user_id=user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user


# ============================================================
# Profile Management
# ============================================================

@router.put(
    "/me",
    response_model=UserResponse,
)
def update_my_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the authenticated user's name or email.

    Users cannot change their own role or account status.
    """
    if (
        user_data.role is not None
        or user_data.status is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You cannot change your role "
                "or account status."
            ),
        )

    try:
        return update_user(
            db=db,
            user=current_user,
            name=user_data.name,
            email=user_data.email,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================
# Admin User Management
# ============================================================

@router.put(
    "/{user_id}",
    response_model=UserResponse,
)
def update_existing_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Update a user's name, email, role, or account status.

    Access:
        Admin only.
    """
    user = get_user_by_id(
        db=db,
        user_id=user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    try:
        return update_user(
            db=db,
            user=user,
            name=user_data.name,
            email=user_data.email,
            role=user_data.role,
            status=user_data.status,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_existing_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Delete a user account.

    Access:
        Admin only.

    Restrictions:
        Admins cannot delete their own accounts.
        Users referenced by other records cannot be
        deleted unless those relationships permit it.
    """
    user = get_user_by_id(
        db=db,
        user_id=user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account.",
        )

    try:
        delete_user(
            db=db,
            user=user,
        )

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This user cannot be deleted because "
                "other records reference their account."
            ),
        ) from exc

    return None