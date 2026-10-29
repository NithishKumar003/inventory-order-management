from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from app.database import Base, engine, SessionLocal
from app.models import User
from app.schemas import UserRegister, UserResponse, UserLogin, TokenResponse
from app.security import hash_password, verify_password
from app.auth_token import create_access_token
from app.dependencies import get_current_user
from app.permissions import require_admin

app = FastAPI(
    title="Inventory Management - Authentication Service",
    description="Handles user authentication and authorization.",
    version="1.0.0",
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "authentication-service",
    }

@app.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is alredy registered.",
        )

    new_user = User(
        email=user_data.email,
        hashed_password = hash_password(user_data.password),
        role="customer"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@app.post("/login", response_model=TokenResponse)
def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if not user or not verify_password(
        user_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive."
        )

    access_token = create_access_token(str(user.id))

    return{
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user

@app.get("/admin-test")
def admin_test(
    current_user: User = Depends(require_admin),
):
    return {
        "message": "Administrator access granted.",
        "email": current_user.email,
        "role": current_user.role,
    }
