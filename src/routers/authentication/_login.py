from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from services.auth.service import AuthService
from application.exceptions.responses import EXCEPTION_SCHEMA
from application.exceptions.types import BadRequestException, UnauthorizedException, NotFoundException

__all__ = ("router",)


router = APIRouter(
    prefix="/login",
    route_class=DishkaRoute
)


class UserLoginRequest(BaseModel):
    """
    Model for user login request.
    """
    email: str = Field(..., example="user@example.com")
    password: str = Field(..., example="password", min_length=8)


class UserLoginResponse(BaseModel):
    """
    Model for user login response.
    """
    access_token: str
    token_type: str = "bearer"


documentation = {
    "summary": "User Login",
    "description": "This endpoint allows users to authenticate by providing their email and password.",
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns a JWT token upon successful authentication.",
    "responses": {
        status.HTTP_400_BAD_REQUEST: EXCEPTION_SCHEMA[BadRequestException, "Invalid input data."],
        status.HTTP_401_UNAUTHORIZED: EXCEPTION_SCHEMA[UnauthorizedException, "Invalid credentials provided."],
        status.HTTP_404_NOT_FOUND: EXCEPTION_SCHEMA[NotFoundException, "No user registered with this email."]
    }
}


@router.post("", **documentation)
async def login(data: UserLoginRequest, auth_service: FromDishka[AuthService]) -> UserLoginResponse:
    """
    Endpoint for user authentication.
    """
    jwt_token: str = await auth_service.authenticate_user(
        email=data.email,
        password=data.password
    )
    return UserLoginResponse(
        access_token=jwt_token
    )
