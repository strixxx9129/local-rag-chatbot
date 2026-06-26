# backend/src/auth/dependencies.py
"""
FastAPI dependency injection for authentication.

Usage in routes:
    @router.get("/protected")
    async def protected(current_user: CurrentUser):
        ...

    @router.get("/admin-only")
    async def admin_only(current_user: CurrentSuperuser):
        ...
"""
import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import decode_token, extract_user_id
from src.core.exceptions import ForbiddenError, UnauthorizedError
from src.db.session import get_db_session
from src.models.user import User
from src.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """
    Resolve the Bearer token from the Authorization header,
    validate it, look up the user, and return the ORM instance.

    Raises UnauthorizedError (→ 401) on any failure.
    """
    if not credentials:
        raise UnauthorizedError("Authorization header is missing.")

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise UnauthorizedError("Invalid or expired access token.")

    if payload.get("type") != "access":
        raise UnauthorizedError("Token type mismatch — access token required.")

    user_id: uuid.UUID = extract_user_id(payload)
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)

    if not user:
        raise UnauthorizedError("User account not found.")

    if not user.is_active:
        raise UnauthorizedError("Account is deactivated.")

    return user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require superuser flag on top of normal auth."""
    if not current_user.is_superuser:
        raise ForbiddenError("Superuser privileges required.")
    return current_user


# ── Annotated shorthands for cleaner route signatures ─────────────────────────

CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]