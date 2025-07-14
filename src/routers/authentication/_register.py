from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from routers.common.schemas import SuccessResponse
from services.auth.service import AuthService
from application.exceptions.responses import EXCEPTION_SCHEMA
from application.exceptions.types import BadRequestException, ConflictException

__all__ = ("router",)


router = APIRouter(
    prefix="/signup",
    route_class=DishkaRoute
)


class UserRegistrationRequest(BaseModel):
    """
    Model for user login request.
    """
    email: str = Field(..., example="user@example.com")
    password: str = Field(..., example="password", min_length=8)


documentation = {
    "summary": "User Registration",
    "description": "This endpoint allows users to register by providing their email and password.",
    "status_code": status.HTTP_201_CREATED,
    "response_description": "Returns a success message upon successful registration.",
    "responses": {
        status.HTTP_400_BAD_REQUEST: EXCEPTION_SCHEMA[BadRequestException, "Invalid input data."],
        status.HTTP_409_CONFLICT: EXCEPTION_SCHEMA[ConflictException, "User with this email already exists."],
    }
}


@router.post("", **documentation)
async def register(data: UserRegistrationRequest, auth_service: FromDishka[AuthService]) -> SuccessResponse:
    """
    Endpoint for user registration.
    """
    await auth_service.register_user(
        email=data.email,
        password=data.password
    )
    return SuccessResponse(
        message="User successfully registered"
    )
