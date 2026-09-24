from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.enums.user import UserRole, UserStatus


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
    created_at: datetime
    status: UserStatus

    model_config = ConfigDict(from_attributes=True)