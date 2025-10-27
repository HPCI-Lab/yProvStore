from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import DishkaRoute

from application.exceptions.responses import EXCEPTION_SCHEMA
from application.exceptions.types import UnauthorizedException, ForbiddenException
from application.documentation.openapi_generation import EXAMPLE_EMAIL
from routers.common.dependencies import LoggedUser


__all__ = ("router",)


router = APIRouter(
    prefix="/verify",
    route_class=DishkaRoute,
)


class UserVerifyResponse(BaseModel):
    """
    Response model for user verification.
    """
    email: str = Field(..., examples=[EXAMPLE_EMAIL])


documentation = {
    "summary": "Verify token status",
    "description": "This endpoint verifies if the token is valid and returns the email of the authenticated user.",
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns the email of the authenticated user if the token is valid.",
    "responses": {
        status.HTTP_401_UNAUTHORIZED: EXCEPTION_SCHEMA[UnauthorizedException, "Invalid or expired token."],
        status.HTTP_403_FORBIDDEN: EXCEPTION_SCHEMA[ForbiddenException, "Access denied."],
    },
}


@router.post("", **documentation)
async def login(logged_user: LoggedUser) -> UserVerifyResponse:
    """
    Endpoint for user authentication.
    """
    return UserVerifyResponse(
        email=logged_user.email
    )
