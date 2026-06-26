# backend/src/api/v1/auth.py
"""
Authentication endpoints.

Routes are intentionally thin — they validate input via Pydantic,
call the service, and return the response. Zero business logic here.

Endpoints:
  POST /auth/register      → create account, return tokens
  POST /auth/login         → authenticate, return tokens
  POST /auth/refresh       → rotate refresh token, return new access token
  POST /auth/logout        → revoke refresh token
  GET  /auth/me            → return current user profile
  PUT  /auth/me/password   → change password
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.db.session import get_db_session
from src.schemas.auth import (
    AccessTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from src.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthService:
    return AuthService(session)


AuthServiceDep = Annotated[AuthService, Depends(_get_auth_service)]


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    data: RegisterRequest,
    service: AuthServiceDep,
) -> TokenResponse:
    return await service.register(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive access + refresh tokens",
)
async def login(
    data: LoginRequest,
    service: AuthServiceDep,
) -> TokenResponse:
    return await service.login(data.email, data.password)


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Rotate refresh token and get new access token",
)
async def refresh(
    data: RefreshRequest,
    service: AuthServiceDep,
) -> AccessTokenResponse:
    return await service.refresh(data.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout — revoke refresh token",
)
async def logout(
    current_user: CurrentUser,
    service: AuthServiceDep,
) -> MessageResponse:
    await service.logout(current_user.id)
    return MessageResponse(message="Logged out successfully.")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the authenticated user's profile",
)
async def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.put(
    "/me/password",
    response_model=MessageResponse,
    summary="Change password",
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: CurrentUser,
    service: AuthServiceDep,
) -> MessageResponse:
    await service.change_password(
        current_user.id,
        data.current_password,
        data.new_password,
    )
    return MessageResponse(message="Password changed successfully.")