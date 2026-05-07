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

    def __init__(self, message: str, details: dict | None = None):
        self.details = details or {}
        super().__init__("validation_error", message)


class ConflictError(CanonicalError):
    """Request conflicts with current state (e.g. already running)."""

    def __init__(self, message: str):
        super().__init__("conflict", message)


class ConcurrencyConflictError(ConflictError):
    """A concurrent operation is already holding the requested resource."""

    def __init__(self, resource: str, resource_id: str, reason: str):
        self.resource = resource
        self.resource_id = resource_id
        self.reason = reason
        super().__init__(f"conflict on {resource}({resource_id}): {reason}")

    def to_response(self):
        return {
            "error": "conflict",
            "resource": self.resource,
            "resource_id": self.resource_id,
            "reason": self.reason,
        }
