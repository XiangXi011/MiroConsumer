"""Canonical exception types for application-service boundaries.

These exceptions subclass ValueError so existing ``except ValueError``
handlers in API routes continue to work unchanged.  They add a stable
``code`` attribute that tests and observability can rely on regardless
of locale or human-readable message changes.
"""


class CanonicalError(ValueError):
    """Base for all machine-readable app-service errors.

    Attributes:
        code: Stable machine-readable error category (e.g. ``"not_found"``).
    """

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class NotFoundError(CanonicalError):
    """Requested entity does not exist."""

    def __init__(self, message: str):
        super().__init__("not_found", message)


class ValidationError(CanonicalError):
    """Input failed business-rule or shape validation."""

    def __init__(self, message: str):
        super().__init__("validation_error", message)


class ConflictError(CanonicalError):
    """Request conflicts with current state (e.g. already running)."""

    def __init__(self, message: str):
        super().__init__("conflict", message)
