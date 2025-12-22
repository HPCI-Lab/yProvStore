from typing import Any
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExceptionResponse:
    description: str


@dataclass(frozen=True, slots=True)
class ValidationExceptionResponse(ExceptionResponse):
    details: list[dict[str, Any]] | None = None


class ExceptionSchema:
    BadRequestException = {
        "model": ValidationExceptionResponse,
        "description": "Bad request. The server could not understand the request due to invalid syntax.",
        "status_code": 400,
    }
    UnauthorizedException = {
        "model": ExceptionResponse,
        "description": "Unauthorized access. Invalid or expired authentication token.",
        "status_code": 401
    }
    ForbiddenException = {
        "model": ExceptionResponse,
        "description": "Forbidden access. You do not have permission to perform this action.",
        "status_code": 403,
    }
    NotFoundException = {
        "model": ExceptionResponse,
        "description": "Resource not found. The requested resource could not be found on the server.",
        "status_code": 404,
    }
    ConflictException = {
        "model": ExceptionResponse,
        "description": "Conflict. The request could not be completed due to a conflict with the current state of the resource.",
        "status_code": 409,
    }
    PayloadTooLargeException = {
        "model": ExceptionResponse,
        "description": "Payload too large. The request or response payload exceeds the server's limit.",
        "status_code": 413,
    }
    InternalServerErrorException = {
        "model": ExceptionResponse,
        "description": "Internal server error. The server encountered an unexpected condition that prevented it from fulfilling the request.",
        "status_code": 500,
    }
    ServiceUnavailableException = {
        "model": ExceptionResponse,
        "description": "Service unavailable. The server is currently unable to handle the request due to a failed connection to a required service.",
        "status_code": 503,
    }

    def __getitem__(self, item: type | tuple, description: str | None = None) -> dict[str, Any]:
        """
        Get the exception response schema for a given exception type.

        :param item: The exception type.
        :return: A dictionary containing the model and description for the exception.
        """
        if isinstance(item, tuple):
            description = item[1] if len(item) > 1 else None
            if len(item) < 1:
                raise Exception("Exception type must be provided.")
            item = item[0]
            if not isinstance(item, type):
                raise TypeError("Expected a type for the exception, got: {}".format(type(item)))
        schema = self.__class__.__dict__.get(item.__name__, {"model": ExceptionResponse, "description": "An error occurred."})
        if description:
            schema["description"] = description
        return schema


EXCEPTION_SCHEMA = ExceptionSchema()
