from fastapi import Depends, HTTPException, status

from app.dependencies import get_current_user
from app.models import User


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )

    return current_user


def require_inventory_manager(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in ("admin", "inventory_manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inventory manager access required.",
        )

    return current_user