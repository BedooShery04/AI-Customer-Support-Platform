from sqlalchemy.orm import Session

from app.enums.user import UserRole, UserStatus
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.auth_service import hash_password


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """
    Retrieve a user by their ID.
    """

    return (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )


def get_user_by_email(db: Session, email: str) -> User | None:
    """
    Retrieve a user by their email.
    """

    return (
        db.query(User)
        .filter(User.email == email)
        .first()
    )


def create_user(db: Session, user_data: UserCreate) -> User:
    """
    Create a new user.

    The password is hashed before being stored.
    """

    existing_user = get_user_by_email(
        db,
        user_data.email
    )

    if existing_user:
        raise ValueError(
            "A user with this email already exists."
        )

    hashed_password = hash_password(
        user_data.password
    )

    user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password,
        role=UserRole.CUSTOMER,
        status=UserStatus.ACTIVE
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_users(db: Session) -> list[User]:
    """
    Retrieve all users.
    """

    return db.query(User).all()


def update_user(
    db: Session,
    user: User,
    name: str | None = None,
    email: str | None = None,
    role: UserRole | None = None,
    status: UserStatus | None = None
) -> User:
    """
    Update user information.
    """

    if name is not None:
        user.name = name

    if email is not None:
        user.email = email

    if role is not None:
        user.role = role

    if status is not None:
        user.status = status

    db.commit()
    db.refresh(user)

    return user


def delete_user(db: Session, user: User) -> None:
    """
    Delete a user from the database.
    """

    db.delete(user)
    db.commit()