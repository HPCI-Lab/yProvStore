from passlib.context import CryptContext
from dishka import Provider, provide, Scope
from starlette.requests import Request

from application.exceptions.types import ConflictException, NotFoundException, BadRequestException, UnauthorizedException
from services.auth._token_manager import TokenManager
from services.user_storage.service import UserStorageService
from models import User, TokenData


class AuthService:

    def __init__(self, user_storage: UserStorageService, request: Request):
        self._user_storage = user_storage
        self.request = request
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async def register_user(self, email: str, password: str) -> User:
        """
        Register a new user with the given email and password.

        :raises BadRequestException: if email or password is not provided.
        :raises ConflictException: if a user with the given email already exists.
        :return: User object representing the newly registered user.
        """
        if not email or not password:
            raise BadRequestException("Email and password must be provided.")
        existing_user = await self._user_storage.get_user_by_email(email, raise_not_found=False)
        if existing_user:
            raise ConflictException(f"User with email '{email}' already exists.")

        hashed_password = self._hash_password(password)
        user = User(email=email, password_hash=hashed_password)
        await self._user_storage.save_user(user)
        return user

    async def authenticate_user(self, email: str, password: str) -> str:
        """
        Authenticate a user with the given email and password.

        :raises BadRequestException: if the credentials are invalid.
        :raises NotFoundException: if no user is registered with the given email.
        :return: JWT token for the authenticated user.
        """
        if not email or not password:
            raise BadRequestException("Email and password must be provided.")

        user = await self._user_storage.get_user_by_email(email)
        if not user:
            raise NotFoundException(f"No user registered with email '{email}'.")

        if not self._verify_password(password, user.password_hash):
            raise BadRequestException("Invalid credentials provided.")

        jwt_token = TokenManager.create_access_token(TokenData(email=user.email))

        return jwt_token

    async def get_authenticated_user(self, token: str) -> User:
        """
        Get the authenticated user based on the provided JWT token.

        :raises UnauthorizedException: if the token is invalid or expired.
        :raises NotFoundException: if the user cannot be found.
        :return: User object representing the authenticated user.
        """
        if not token:
            raise UnauthorizedException("No valid JWT token provided.")
        token_data = TokenManager.decode_token(token)
        user = await self._user_storage.get_user_by_email(token_data.email)
        if not user:
            raise NotFoundException(f"User with email '{token_data.email}' not found.")
        return user

    def _hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(password, hashed_password)


class AuthServiceProvider(Provider):

    auth_service = provide(AuthService, scope=Scope.REQUEST)
