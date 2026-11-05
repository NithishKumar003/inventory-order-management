import hmac
import os

from fastapi import Header
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, RefreshToken, AuditLog
from app.schemas import (
    UserRegister,
    UserResponse,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    UserRoleUpdate,
)
from app.security import hash_password, verify_password
from app.auth_token import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    get_refresh_token_expiry,
)
from app.dependencies import get_current_user
from app.permissions import require_admin


app = FastAPI(
    title="Inventory Management - Authentication Service",
    description="Handles user authentication and authorization.",
    version="1.0.0",
)


# DATABASE CONNECTION

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# AUDIT LOG HELPER

def create_audit_log(
    db: Session,
    action: str,
    request: Request,
    user: User = None,
    email: str = None,
    details: str = None,
):
    log = AuditLog(
        user_id=user.id if user else None,
        email=email or (user.email if user else None),
        action=action,
        ip_address=request.client.host if request.client else None,
        details=details,
    )

    db.add(log)


# HEALTH CHECK

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "authentication-service",
    }


# USER REGISTRATION

@app.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: UserRegister,
    request: Request,
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
            detail="Email is already registered.",
        )

    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role="customer",
    )

    db.add(new_user)
    db.flush()

    create_audit_log(
        db,
        "USER_REGISTERED",
        request,
        user=new_user,
    )

    db.commit()
    db.refresh(new_user)

    return new_user


# USER LOGIN

@app.post("/login", response_model=TokenResponse)
def login_user(
    user_data: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if not user or not verify_password(
        user_data.password,
        user.hashed_password if user else "",
    ):
        create_audit_log(
            db,
            "LOGIN_FAILED",
            request,
            email=user_data.email,
            details="Invalid credentials",
        )
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        create_audit_log(
            db,
            "LOGIN_FAILED",
            request,
            user=user,
            details="Inactive account",
        )
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token()

    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=get_refresh_token_expiry(),
    )

    db.add(refresh_token_record)

    create_audit_log(
        db,
        "LOGIN_SUCCESS",
        request,
        user=user,
    )

    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


# REFRESH ACCESS TOKEN

@app.post("/refresh", response_model=TokenResponse)
def refresh_access_token(
    token_data: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    submitted_token_hash = hash_refresh_token(
        token_data.refresh_token
    )

    stored_token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == submitted_token_hash)
        .first()
    )

    if stored_token is None or stored_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked refresh token.",
        )

    expiry = stored_token.expires_at

    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    if expiry <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired.",
        )

    user = (
        db.query(User)
        .filter(User.id == stored_token.user_id)
        .first()
    )

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is unavailable.",
        )

    stored_token.is_revoked = True

    new_access_token = create_access_token(str(user.id))
    new_refresh_token = create_refresh_token()

    new_refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(new_refresh_token),
        expires_at=get_refresh_token_expiry(),
    )

    db.add(new_refresh_record)

    create_audit_log(
        db,
        "TOKEN_REFRESHED",
        request,
        user=user,
    )

    db.commit()

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


# USER LOGOUT

@app.post("/logout")
def logout_user(
    token_data: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    token_hash = hash_refresh_token(token_data.refresh_token)

    stored_token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )

    if stored_token is None or stored_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or already revoked refresh token.",
        )

    stored_token.is_revoked = True

    user = (
        db.query(User)
        .filter(User.id == stored_token.user_id)
        .first()
    )

    create_audit_log(
        db,
        "LOGOUT",
        request,
        user=user,
        details="Refresh token revoked",
    )

    db.commit()

    return {
        "message": "Logged out successfully."
    }


# CURRENT USER PROFILE

@app.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user


# ADMIN TEST

@app.get("/admin-test")
def admin_test(
    current_user: User = Depends(require_admin),
):
    return {
        "message": "Administrator access granted.",
        "email": current_user.email,
        "role": current_user.role,
    }


# LIST CUSTOMERS

@app.get("/admin/customers")
def list_customers(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    customers = (
        db.query(User)
        .filter(User.role == "customer")
        .order_by(User.id.desc())
        .all()
    )

    return [
        {
            "id": customer.id,
            "email": customer.email,
            "role": customer.role,
            "is_active": customer.is_active,
            "created_at": customer.created_at,
        }
        for customer in customers
    ]


# UPDATE USER ROLE

@app.put("/admin/users/{user_id}/role")
def update_user_role(
    user_id: int,
    role_data: UserRoleUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    old_role = user.role
    user.role = role_data.role

    create_audit_log(
        db,
        "USER_ROLE_UPDATED",
        request,
        user=current_user,
        details=(
            f"User {user.id}: "
            f"{old_role} -> {role_data.role}"
        ),
    )

    db.commit()

    return {
        "message": "User role updated successfully.",
        "user_id": user.id,
        "role": user.role,
    }


# VIEW AUDIT LOGS

@app.get("/admin/audit-logs")
def list_audit_logs(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.id.desc())
        .limit(100)
        .all()
    )

    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "email": log.email,
            "action": log.action,
            "ip_address": log.ip_address,
            "details": log.details,
            "created_at": log.created_at,
        }
        for log in logs
    ]
    
# INTERNAL ADMIN LOOKUP

@app.get("/internal/admin-ids")
def get_active_admin_ids(
    x_internal_service_token: str | None = Header(
        default=None,
        alias="X-Internal-Service-Token",
    ),
    db: Session = Depends(get_db),
):
    expected_token = os.getenv("INTERNAL_SERVICE_TOKEN", "")

    if (
        not expected_token
        or not x_internal_service_token
        or not hmac.compare_digest(
            x_internal_service_token,
            expected_token,
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid internal service token.",
        )

    admin_ids = (
        db.query(User.id)
        .filter(
            User.role == "admin",
            User.is_active.is_(True),
        )
        .all()
    )

    return {
        "admin_ids": [admin_id for (admin_id,) in admin_ids]
    }