"""Domain-specific exceptions."""


class ReproWeaveError(Exception):
    """Base error for expected user-facing failures."""


class ValidationError(ReproWeaveError):
    """Raised when an artifact violates the documented data model."""


class ReferenceError(ValidationError):
    """Raised when an artifact points to a missing object."""


class CycleError(ValidationError):
    """Raised when replication tasks form a dependency cycle."""
