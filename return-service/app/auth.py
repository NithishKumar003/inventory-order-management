
import os
from pathlib import Path

import httpx
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


SERVICE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SERVICE_DIR / ".env")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
AUTH_SERVICE_URL = os.getenv(
    "AUTH_SERVICE_URL",
    "http://127.0.0.1:8001",
)

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if not JWT_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Authentication is not configured.",
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        user_id = int(payload.get("sub"))

        if user_id <= 0:
            raise ValueError("Invalid user ID.")

    except (jwt.InvalidTokenError, TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token.",
        )

    try:
        response = httpx.get(
            f"{AUTH_SERVICE_URL}/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5.0,
        )
        response.raise_for_status()
        user = response.json()

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Authentication service is unavailable.",
        )
    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=401,
            detail="Unable to authenticate user.",
        )

    if user.get("id") != user_id:
        raise HTTPException(
            status_code=401,
            detail="Authenticated user does not match token.",
        )

    # Keep the verified token available for Order Service communication.
    user["_access_token"] = token

    return user
