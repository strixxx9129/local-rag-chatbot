# backend/src/services/auth_service.py
"""
Auth business logic — registration, login, token refresh, logout.

The service layer sits between the API routes and the repository.
It orchestrates operations, enforces business rules, and calls
auth utilities. It NEVER writes raw SQL.
"""
import uuid

from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    extract_user_id,
)
from src.auth.password import hash_password, verify_password
from src.core.exceptions import (
    BadRequestError,
    ConflictError,
    UnauthorizedError,
)
from src.core.logging import logger
from src.models.user import User
from src.repositories.user_repository import UserRepository
from src.schemas.auth import (
    AccessTokenResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = UserRepository(session)

    # ── Registration ──────────────────────────────────────────────────────────

    async def register(self, data: RegisterRequest) -> TokenResponse:
        """
        Create a new user account and return tokens immediately.

        Checks both email and username uniqueness before writing to DB.
        """
        if await self._repo.email_exists(data.email):
            raise ConflictError("An account with this email already exists.")

        if await self._repo.username_exists(data.username):
            raise ConflictError("This username is already taken.")

        user = await self._repo.create(
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
        )

        return await self._issue_tokens(user)

    # ── Login ─────────────────────────────────────────────────────────────────

    async def login(self, email: str, password: str) -> TokenResponse:
        """
        Authenticate a user by email + password.

        Deliberate: we don't distinguish "email not found" from "wrong password"
        in the error message — avoids user enumeration.
        """
        user = await self._repo.get_by_email(email)

        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password.")

        if not user.is_active:
            raise UnauthorizedError("Account is deactivated. Contact support.")

        logger.info("auth.login.success", user_id=str(user.id))
        return await self._issue_tokens(user)

    # ── Token Refresh ─────────────────────────────────────────────────────────

    async def refresh(self, refresh_token: str) -> AccessTokenResponse:
        """
        Rotate the refresh token and return a new access token.

        Rotation strategy:
          1. Decode + verify JWT signature and expiry.
          2. Look up user by the raw token string (DB check ensures
             it hasn't been revoked or already rotated away).
          3. Issue a new access token + rotate the refresh token.

        If the incoming refresh token is valid JWT but NOT in the DB,
        it means it was already rotated (possible token theft).
        We revoke all tokens for that user and raise 401.
        """
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise UnauthorizedError("Invalid or expired refresh token.")

        if payload.get("type") != "refresh":
            raise UnauthorizedError("Token type mismatch.")

        user_id = extract_user_id(payload)

        # Verify token is still in DB (not already rotated away)
        user = await self._repo.get_by_refresh_token(refresh_token)

        if not user:
            # Possible reuse attack — revoke everything for this user
            logger.warning(
                "auth.refresh.token_reuse_detected",
                user_id=str(user_id),
            )
            await self._repo.set_refresh_token(user_id, None)
            raise UnauthorizedError("Refresh token reuse detected. Please log in again.")

        if not user.is_active:
            raise UnauthorizedError("Account is deactivated.")

        # Rotate: issue new access token and replace refresh token in DB
        new_access = create_access_token(user.id)
        new_refresh = create_refresh_token(user.id)
        await self._repo.set_refresh_token(user.id, new_refresh)

        logger.info("auth.refresh.success", user_id=str(user.id))
        return AccessTokenResponse(access_token=new_access)

    # ── Logout ────────────────────────────────────────────────────────────────

    async def logout(self, user_id: uuid.UUID) -> None:
        """Revoke the refresh token — effectively invalidates the session."""
        await self._repo.set_refresh_token(user_id, None)
        logger.info("auth.logout", user_id=str(user_id))

    # ── Change Password ───────────────────────────────────────────────────────

    async def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str,
    ) -> None:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UnauthorizedError("User not found.")

        if not verify_password(current_password, user.hashed_password):
            raise BadRequestError("Current password is incorrect.")

        await self._repo.update_password(user_id, hash_password(new_password))
        logger.info("auth.password_changed", user_id=str(user_id))

    # ── Me ────────────────────────────────────────────────────────────────────

    async def get_me(self, user_id: uuid.UUID) -> UserResponse:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UnauthorizedError("User not found.")
        return UserResponse.model_validate(user)

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _issue_tokens(self, user: User) -> TokenResponse:
        """Create access + refresh tokens, persist refresh token, return response."""
        access = create_access_token(user.id)
        refresh = create_refresh_token(user.id)
        await self._repo.set_refresh_token(user.id, refresh)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            user=UserResponse.model_validate(user),
        )