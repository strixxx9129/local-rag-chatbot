# backend/src/core/exceptions.py
"""
Domain exception hierarchy.

Using typed exceptions (not HTTP status codes) in the service layer
keeps business logic decoupled from transport concerns.
The exception handler in main.py maps them to HTTP responses.
"""


class AppError(Exception):
    """Base exception for all application errors."""
    status_code: int = 500
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    detail = "Resource not found."


class UnauthorizedError(AppError):
    status_code = 401
    detail = "Authentication required."


class ForbiddenError(AppError):
    status_code = 403
    detail = "You do not have permission to perform this action."


class ConflictError(AppError):
    status_code = 409
    detail = "Resource already exists."


class BadRequestError(AppError):
    status_code = 400
    detail = "Invalid request."


class UnprocessableError(AppError):
    status_code = 422
    detail = "Unable to process request."