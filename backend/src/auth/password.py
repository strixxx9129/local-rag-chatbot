# backend/src/auth/password.py
"""
bcrypt password hashing — using the bcrypt package directly.

We bypass passlib entirely because passlib is unmaintained and
incompatible with bcrypt >= 4.0. The bcrypt package itself is
actively maintained and has a clean API.

Work factor 12 = 2^12 iterations (~250ms on modern hardware).
This is the production-standard minimum. Increase to 13 on
hardware where 500ms per hash is acceptable.
"""
import bcrypt


def hash_password(plain: str) -> str:
    """
    Hash a plain-text password with bcrypt.
    Returns a UTF-8 string (bcrypt hash is always ASCII-safe).
    """
    password_bytes = plain.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Return True if plain matches the stored bcrypt hash.
    Uses constant-time comparison internally — safe against timing attacks.
    """
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except Exception:
        # Malformed hash in DB — treat as mismatch, never crash
        return False