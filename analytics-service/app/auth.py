import jwt
import httpx

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import AUTH_SERVICE_URL

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    try:
        jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_exp": True,
                "verify_aud": False,
            },
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
        )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{AUTH_SERVICE_URL}/me",
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Authentication service is unavailable",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail="Authentication failed",
        )

    user = response.json()

    if not isinstance(user, dict) or not user.get("id"):
        raise HTTPException(
            status_code=401,
            detail="Invalid user information",
        )

    return user


async def require_admin(
    user: dict = Depends(get_current_user),
):
    if str(user.get("role", "")).lower() != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator access required",
        )

    return user
