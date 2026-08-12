class ServiceError(Exception):
    """Base error raised by service-layer business rules."""


class ResourceNotFoundError(ServiceError):
    """Raised when a requested vocabulary item or session does not exist."""


class InvalidOperationError(ServiceError):
    """Raised when the resource exists but cannot accept the operation."""

