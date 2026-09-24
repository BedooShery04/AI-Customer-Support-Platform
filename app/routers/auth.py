from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, CurrentUserResponse
from app.schemas.user import UserCreate
from app.services.auth_service import authenticate_user, create_access_token
from app.services.user_service import create_user


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    try:
        user = create_user(
            db=db,
            user_data=user_data
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return {
        "message": "User registered successfully.",
        "user_id": user.id
    }


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = authenticate_user(
        db=db,
        email=login_data.email,
        password=login_data.password
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    access_token = create_access_token(
        user_id=user.id,
        role=user.role
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=CurrentUserResponse)
def get_me(
    current_user: User = Depends(get_current_user)
):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role.value,
        "status": current_user.status.value
    }
