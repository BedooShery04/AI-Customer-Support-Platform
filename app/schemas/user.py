from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.enums import UserRole


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.CUSTOMER


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
    created_at: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)