from typing import Any, cast

import logging
import pydantic
from fastapi.encoders import jsonable_encoder
from fastapi.responses import ORJSONResponse
from starlette import status
from starlette.requests import Request
from sqlalchemy.exc import OperationalError, InterfaceError

from application.exceptions.responses import ExceptionResponse, ValidationExceptionResponse
from application.exceptions.types import UnauthorizedException, ForbiddenException, NotFoundException, ConflictException, \
    InternalServerErrorException, BadRequestException, ServiceUnavailableException, IntegrityException, InternalException


logger = logging.getLogger(__name__)


async def handle_exception(_: Request, exc: Exception) -> ORJSONResponse:
    status_code = resolve_status_code(exc)
    response = build_exception_response(exc, status_code)
    # log_exception(exc, status_code)
    return ORJSONResponse(status_code=status_code, content=jsonable_encoder(response))


def resolve_status_code(exc: Exception) -> int:
    if isinstance(exc, pydantic.ValidationError):
        return status.HTTP_422_UNPROCESSABLE_ENTITY
    error_mapping = {
        ValueError: status.HTTP_400_BAD_REQUEST,
        BadRequestException: status.HTTP_400_BAD_REQUEST,
        UnauthorizedException: status.HTTP_401_UNAUTHORIZED,
        ForbiddenException: status.HTTP_403_FORBIDDEN,
        NotFoundException: status.HTTP_404_NOT_FOUND,
        ConflictException: status.HTTP_409_CONFLICT,
        InternalServerErrorException: status.HTTP_500_INTERNAL_SERVER_ERROR,
        IntegrityException: status.HTTP_500_INTERNAL_SERVER_ERROR,
        InternalException: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ServiceUnavailableException: status.HTTP_503_SERVICE_UNAVAILABLE,
    }
    # === Service-specific unavailable exceptions === #

    # sqlalchemy exceptions
    error_mapping.update({
        TimeoutError: status.HTTP_429_TOO_MANY_REQUESTS,
        OperationalError: status.HTTP_429_TOO_MANY_REQUESTS,
        InterfaceError: status.HTTP_503_SERVICE_UNAVAILABLE
    })

    return error_mapping.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)  # type: ignore


def build_exception_response(exc: Exception, status_code: int) -> ExceptionResponse:
    if isinstance(exc, pydantic.ValidationError):
        return ValidationExceptionResponse(
            description=str(exc),
            details=cast(list[dict[str, Any]], exc.errors()),
        )
    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR and not isinstance(exc, ServiceUnavailableException):
        return ExceptionResponse("Internal server error.")

    return ExceptionResponse(str(exc))


def log_exception(exc: Exception, status_code: int) -> None:
    is_server_error = status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR
    log_func = logger.error if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR else logger.warning

    log_func(
        "Exception '%s' occurred: '%s'.",
        type(exc).__name__,
        exc,
        exc_info=exc if is_server_error else None,
    )
