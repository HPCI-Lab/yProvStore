class UnauthorizedException(Exception):
    """Exception raised for unauthorized access."""
    pass


class ForbiddenException(Exception):
    """Exception raised for forbidden access."""
    pass


class NotFoundException(Exception):
    """Exception raised when a resource is not found."""
    pass


class ConflictException(Exception):
    """Exception raised for conflicts, such as duplicate entries."""
    pass


class BadRequestException(Exception):
    """Exception raised for bad requests, such as invalid input."""
    pass


class PayloadTooLargeException(Exception):
    """Exception raised when the payload is too large."""
    pass


class InternalServerErrorException(Exception):
    """Exception raised for internal server errors."""
    pass


class ServiceUnavailableException(Exception):
    """Exception raised when a service is unavailable."""
    pass


class InternalException(Exception):
    """Exception raised for internal errors that should not be exposed to users."""
    pass


class IntegrityException(Exception):
    """Exception raised for integrity errors, such as database constraints."""
    pass
