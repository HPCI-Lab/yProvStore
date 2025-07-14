from fastapi.security import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from starlette.requests import Request

from models import User
from services.auth.service import AuthService
from application.exceptions.types import UnauthorizedException


class JWTTokenBearer(HTTPBearer):
    """
    Custom security scheme for JWT token authentication.
    This class extends HTTPBearer to provide a custom authentication mechanism
    using JWT tokens.
    It verifies the token using the AuthService and raises an exception
    if the token is invalid.
    If the token is valid, it sets the authenticated user in the request state.
    """

    async def __call__(
        self,
        request: Request,
    ) -> User:

        authorization = request.headers.get("Authorization")
        scheme, credentials = get_authorization_scheme_param(authorization)

        if scheme.lower() != "bearer" or not credentials:
            raise UnauthorizedException("Invalid or missing Authorization header")

        # Added automatically by the setup_dishka function
        dishka_container = request.state.dishka_container

        auth_service: AuthService = await dishka_container.get(AuthService)

        request.state.user = await auth_service.get_authenticated_user(credentials)
        return request.state.user


jwt_token_bearer = JWTTokenBearer()
