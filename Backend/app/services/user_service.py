
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.enums.user import UserRole, UserStatus
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.auth_service import hash_password


# ============================================================
# User Retrieval
# ============================================================

def get_user_by_id(
    db: Session,
    user_id: int,
) -> User | None:
    """
    Retrieve a user by their ID.

    Args:
        db: The active database session.
        user_id: The user's ID.

    Returns:
        The matching User, or None if the user does not exist.
    """
    return (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    """
    Retrieve a user by email using case-insensitive matching.

    Args:
        db: The active database session.
        email: The email address to search for.

    Returns:
        The matching User, or None if no user exists.
    """
    normalized_email = email.strip().lower()

    return (
        db.query(User)
        .filter(func.lower(User.email) == normalized_email)
        .first()
    )


def get_users(db: Session) -> list[User]:
    """
    Retrieve all users.

    Args:
        db: The active database session.

    Returns:
        A list of all users.
    """
    return db.query(User).all()


# ============================================================
# User Creation
# ============================================================

def create_user(
    db: Session,
    user_data: UserCreate,
) -> User:
    """
    Register a customer or agent account.

    Customer accounts are activated immediately.
    Agent accounts require admin approval.
    Admin accounts cannot be created through registration.

    Args:
        db: The active database session.
        user_data: The validated registration data.

    Returns:
        The newly created User.

    Raises:
        ValueError: If the email already exists or the
            requested role is not allowed.
    """
    normalized_email = user_data.email.strip().lower()

    if get_user_by_email(db, normalized_email):
        raise ValueError(
            "A user with this email already exists."
        )

    if user_data.role not in (
        UserRole.CUSTOMER,
        UserRole.AGENT,
    ):
        raise ValueError(
            "Only customer and agent registration is allowed."
        )

    user_status = (
        UserStatus.SUSPENDED
        if user_data.role == UserRole.AGENT
        else UserStatus.ACTIVE
    )

    user = User(
        name=user_data.name,
        email=normalized_email,
        password_hash=hash_password(user_data.password),
        role=user_data.role,
        status=user_status,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)

    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "A user with this email already exists."
        ) from exc

    return user


# ============================================================
# User Updates
# ============================================================

def update_user(
    db: Session,
    user: User,
    name: str | None = None,
    email: str | None = None,
    role: UserRole | None = None,
    status: UserStatus | None = None,
) -> User:
    """
    Update an existing user's information.

    Only the fields provided are updated. Email addresses
    are normalized and checked for duplicates.

    The calling router must enforce authorization before
    allowing role or status changes.

    Args:
        db: The active database session.
        user: The user to update.
        name: The new name, if provided.
        email: The new email address, if provided.
        role: The new user role, if provided.
        status: The new account status, if provided.

    Returns:
        The updated User.

    Raises:
        ValueError: If the new email belongs to another user
            or a database constraint is violated.
    """
    if name is not None:
        user.name = name

    if email is not None:
        normalized_email = email.strip().lower()

        existing_user = get_user_by_email(
            db,
            normalized_email,
        )

        if (
            existing_user is not None
            and existing_user.id != user.id
        ):
            raise ValueError(
                "A user with this email already exists."
            )

        user.email = normalized_email

    if role is not None:
        user.role = role

    if status is not None:
        user.status = status

    try:
        db.commit()
        db.refresh(user)

    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "The update violates a database constraint."
        ) from exc

    return user


# ============================================================
# User Deletion
# ============================================================

def delete_user(
    db: Session,
    user: User,
) -> None:
    """
    Delete a user from the database.

    Args:
        db: The active database session.
        user: The user to delete.

    Note:
        Deletion may fail if other records still reference
        the user through foreign keys.
    """
    db.delete(user)
    db.commit()