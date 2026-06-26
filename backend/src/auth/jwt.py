# backend/src/auth/jwt.py
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from src.core.config import settings
from src.core.logging import logger


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: uuid.UUID) -> str:
    now = _utc_now()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,       # ← your key name
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    now = _utc_now()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_token_expire_days),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,       # ← your key name
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,   # ← your key name
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as exc:
        logger.warning("jwt.decode.failed", error=str(exc))
        raise


def extract_user_id(payload: dict[str, Any]) -> uuid.UUID:
    sub = payload.get("sub")
    if not sub:
        raise JWTError("Token missing 'sub' claim")
    return uuid.UUID(sub)