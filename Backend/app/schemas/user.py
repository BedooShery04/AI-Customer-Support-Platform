from datetime import datetime

import re

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    
)

from app.enums.user import UserRole, UserStatus



class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: UserRole = UserRole.CUSTOMER

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = " ".join(value.split())

        if len(value) < 2:
            raise ValueError("Name must contain at least 2 characters.")

        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 bytes.")

        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain an uppercase letter.")

        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain a lowercase letter.")

        if not re.search(r"\d", value):
            raise ValueError("Password must contain a number.")

        if not re.search(r"[^A-Za-z0-9]", value):
            raise ValueError("Password must contain a special character.")

        return value

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: UserRole) -> UserRole:
        if value not in (UserRole.CUSTOMER, UserRole.AGENT):
            raise ValueError("Only customer and agent registration is allowed.")

        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )
    email: EmailStr | None = None
    role: UserRole | None = None
    status: UserStatus | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = " ".join(value.split())

        if len(value) < 2:
            raise ValueError(
                "Name must contain at least 2 characters."
            )

        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if value is not None else None


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
    created_at: datetime
    status: UserStatus

    model_config = ConfigDict(from_attributes=True)