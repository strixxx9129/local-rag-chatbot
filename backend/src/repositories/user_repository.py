# backend/src/repositories/user_repository.py
"""
All database operations for the User model.

The repository is the ONLY place that runs SQL.
Services call the repository — they never run queries directly.
"""
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_refresh_token(self, token: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.refresh_token == token)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        username: str,
        hashed_password: str,
        full_name: str | None = None,
    ) -> User:
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
        )
        self._session.add(user)
        await self._session.flush()   # populate id without committing
        await self._session.refresh(user)
        return user

    async def set_refresh_token(
        self,
        user_id: uuid.UUID,
        token: str | None,
    ) -> None:
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(refresh_token=token)
        )

    async def update_password(
        self,
        user_id: uuid.UUID,
        hashed_password: str,
    ) -> None:
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(hashed_password=hashed_password, refresh_token=None)
        )

    async def deactivate(self, user_id: uuid.UUID) -> None:
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=False, refresh_token=None)
        )

    async def email_exists(self, email: str) -> bool:
        result = await self._session.execute(
            select(User.id).where(User.email == email)
        )
        return result.scalar_one_or_none() is not None

    async def username_exists(self, username: str) -> bool:
        result = await self._session.execute(
            select(User.id).where(User.username == username)
        )
        return result.scalar_one_or_none() is not None