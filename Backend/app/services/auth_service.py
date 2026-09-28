
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.enums.user import UserRole, UserStatus
from app.models.user import User


# ============================================================
# Configuration
# ============================================================

load_dotenv()

JWT_SECRET_KEY = os.getenv("SECRET_KEY")
JWT_ALGORITHM = os.getenv("ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


# ============================================================
# Password Utilities
# ============================================================

def hash_password(password: str) -> str:
    """
    Hash a plain-text password before storing it in the database.

    Args:
        password: The user's plain-text password.

    Returns:
        The bcrypt password hash.
    """
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Check whether a plain-text password matches a stored hash.

    Args:
        plain_password: The password provided by the user.
        hashed_password: The password hash stored in the database.

    Returns:
        True if the password matches; otherwise, False.
    """
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


# ============================================================
# User Authentication
# ============================================================

def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    """
    Authenticate a user using their email and password.

    Email matching is case-insensitive. Suspended and inactive
    accounts cannot log in.

    Args:
        db: The active database session.
        email: The user's email address.
        password: The user's plain-text password.

    Returns:
        The authenticated User, or None if the credentials
        are incorrect.

    Raises:
        ValueError: If the account is suspended or inactive.
    """
    normalized_email = email.strip().lower()

    user = (
        db.query(User)
        .filter(func.lower(User.email) == normalized_email)
        .first()
    )

    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    if user.status == UserStatus.SUSPENDED:
        raise ValueError(
            "Your account is waiting for admin approval."
        )

    if user.status == UserStatus.INACTIVE:
        raise ValueError(
            "Your account has been deactivated."
        )

    return user


# ============================================================
# JWT Utilities
# ============================================================

def create_access_token(
    user_id: int,
    role: UserRole,
) -> str:
    """
    Create a signed JWT access token.

    The token contains the user's ID, role, and expiration
    timestamp.

    Args:
        user_id: The authenticated user's ID.
        role: The authenticated user's role.

    Returns:
        The encoded JWT access token.

    Raises:
        RuntimeError: If SECRET_KEY is not configured.
    """
    if not JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured."
        )

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "role": role.value,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict | None:
    """
    Decode and validate a JWT access token.

    Args:
        token: The encoded JWT access token.

    Returns:
        The decoded token payload, or None if the token
        is invalid or expired.

    Raises:
        RuntimeError: If SECRET_KEY is not configured.
    """
    if not JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured."
        )

    try:
        return jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

    except JWTError:
        return None