"""Application exception hierarchy.

Domain/service code raises these provider-agnostic exceptions; a single FastAPI
exception handler (``app.api.errors``) maps them to HTTP responses. This keeps
business logic free of HTTP concerns and gives every error a stable
``code`` clients can branch on.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all expected/handled application errors."""

    status_code: int = 500
    code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, *, code: str | None = None) -> None:
        self.message = message or self.message
        if code is not None:
            self.code = code
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "Resource not found."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message = "Resource already exists."


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"
    message = "Validation failed."


class AuthenticationError(AppError):
    status_code = 401
    code = "authentication_error"
    message = "Could not validate credentials."


class PermissionDeniedError(AppError):
    status_code = 403
    code = "permission_denied"
    message = "You do not have permission to perform this action."


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"
    message = "Too many requests. Please slow down."


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"
    message = "This service is temporarily unavailable."
