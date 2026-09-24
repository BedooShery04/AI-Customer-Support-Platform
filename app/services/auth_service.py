import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.enums import UserRole
from app.models.user import User


load_dotenv()


# ============================================================
# JWT Configuration
# ============================================================

JWT_SECRET_KEY = os.getenv("SECRET_KEY")
JWT_ALGORITHM = os.getenv("ALGORITHM", "HS256")

JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "60"
    )
)


# ============================================================
# Password Hashing
# ============================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using bcrypt.

    The returned hash is safe to store in the database.
    """

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a stored hash.
    """

    return pwd_context.verify(
        plain_password,
        hashed_password
    )


# ============================================================
# User Authentication
# ============================================================

def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """
    Authenticate a user using email and password.

    Returns:
        User object if authentication succeeds.
        None if authentication fails.
    """

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    # User does not exist
    if user is None:
        return None

    # User account is disabled/inactive
    if user.status != "active":
        return None

    # Password is incorrect
    if not verify_password(
        password,
        user.password_hash
    ):
        return None

    return user


# ============================================================
# JWT Token Creation
# ============================================================

def create_access_token(user_id: int, role: UserRole) -> str:
    """
    Create a JWT access token for an authenticated user.

    JWT payload contains:
        sub  -> user ID
        role -> user role
        exp  -> expiration time
    """

    if not JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured."
        )

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": str(user_id),
        "role": role.value,
        "exp": expire
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )


# ============================================================
# JWT Token Decoding
# ============================================================

def decode_access_token(token: str) -> dict | None:
    """
    Decode and validate a JWT access token.

    Returns:
        Dictionary containing JWT payload if valid.
        None if token is invalid or expired.
    """

    if not JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured."
        )

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        return payload

    except JWTError:
        return None