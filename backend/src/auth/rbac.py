# backend/src/auth/rbac.py
"""
Role-based access control helpers.

These are thin guard functions — call them inside service methods
to enforce ownership or role checks that can't be expressed as
simple dependencies.
"""
import uuid

from src.core.exceptions import ForbiddenError
from src.models.user import User


def require_owner_or_superuser(
    resource_owner_id: uuid.UUID,
    current_user: User,
    resource_name: str = "resource",
) -> None:
    """
    Raise ForbiddenError unless the current user owns the resource
    or is a superuser.

    Usage:
        require_owner_or_superuser(document.user_id, current_user, "document")
    """
    if current_user.is_superuser:
        return
    if current_user.id != resource_owner_id:
        raise ForbiddenError(
            f"You do not have permission to access this {resource_name}."
        )


def require_superuser(current_user: User) -> None:
    """Raise ForbiddenError if user is not a superuser."""
    if not current_user.is_superuser:
        raise ForbiddenError("Superuser privileges required.")