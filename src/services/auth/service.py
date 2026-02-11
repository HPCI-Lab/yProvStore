import logging
import base64
import requests
from abc import abstractmethod
import secrets

from passlib.context import CryptContext
from dishka import Provider, provide, Scope
from starlette.requests import Request

from application.settings import EGI_CHECKIN_REQUIRED_ENTITLEMENTS, EGI_CHECKIN_CLIENT_ID, EGI_CHECKIN_CLIENT_SECRET, \
    EGI_CHECKIN_INTROSPECTION_ENDPOINT, USE_EGI_CHECKIN_AUTH
from application.exceptions.types import ConflictException, NotFoundException, BadRequestException, UnauthorizedException
from services.auth._token_manager import TokenManager
from services.user_storage.service import UserStorageService
from models import User, TokenData

logger = logging.getLogger(__name__)


class AuthService:

    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @abstractmethod
    async def register_user(self, email: str, password: str) -> User:
        """
        Register a new user with the given email and password.

        :raises BadRequestException: if email or password is not provided.
        :raises ConflictException: if a user with the given email already exists.
        :return: User object representing the newly registered user.
        """
        pass

    @abstractmethod
    async def authenticate_user(self, email: str, password: str) -> str:
        """
        Authenticate a user with the given email and password.

        :raises BadRequestException: if the credentials are invalid.
        :raises NotFoundException: if no user is registered with the given email.
        :return: JWT token for the authenticated user.
        """
        pass

    @abstractmethod
    async def get_authenticated_user(self, token: str) -> User:
        """
        Get the authenticated user based on the provided JWT token.

        :raises UnauthorizedException: if the token is invalid or expired.
        :raises NotFoundException: if the user cannot be found.
        :return: User object representing the authenticated user.
        """
        pass

    def _hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(password, hashed_password)


class JWTAuthService(AuthService):

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
    

class EGIAuthService(AuthService):

    def __init__(self, user_storage: UserStorageService, request: Request):
        super().__init__()
        self.user_storage = user_storage
        self.request = request
        # self.auth_header = f"Bearer {EGI_CHECKIN_CLIENT_ID}:{EGI_CHECKIN_CLIENT_SECRET}"
        self.auth_header = "Basic " + base64.b64encode(f"{EGI_CHECKIN_CLIENT_ID}:{EGI_CHECKIN_CLIENT_SECRET}".encode()).decode()

    async def register_user(self, email: str, password: str) -> User:
        """
        EGI AAI does not support user registration through the application.
        """
        raise NotImplementedError

    async def authenticate_user(self, email: str, password: str) -> str:
        """
        EGI AAI authentication is handled externally and does not involve password verification within the application.
        """
        raise NotImplementedError

    async def get_authenticated_user(self, token: str) -> User:
        """
        EGI AAI authentication is handled through token introspection.
        This method validates the provided token and checks for required entitlements.
        """

        token = None
        if "Authorization" in self.request.headers:
            token = self.request.headers["Authorization"].split(" ")[1]

        if not token:
            raise UnauthorizedException("No valid token provided.")
        try:
            introspection_response = self._introspect_token(token)

            if not introspection_response:
                raise UnauthorizedException("Token is invalid")

            active = introspection_response.get("active", False)

            # Check if entitlements claim is present
            entitlements = introspection_response.get("entitlements", [])
            entitlements_str = " ".join(entitlements)

            if not active:
                raise UnauthorizedException("Token is invalid")

            # Check if ANY of the required entitlements are present
            if not any(entitlement in entitlements for entitlement in EGI_CHECKIN_REQUIRED_ENTITLEMENTS):
                raise UnauthorizedException("None of the required entitlements found: "+ str(EGI_CHECKIN_REQUIRED_ENTITLEMENTS))
            # Success: Return pretty-printed JSON
            _id = introspection_response.get("voperson_id", None)
            email = introspection_response.get("email", None)
            username = introspection_response.get("preferred_username", None)
            if not _id:
                _id = username
            if not email:
                email = username

            #TODO: remove these logs
            # print(list(introspection_response.keys()))
            # print(f"Token is valid. User: {username}, Entitlements: {entitlements_str}")

            existing_user = await self.user_storage.get_user_by_email(email, raise_not_found=False)
            if not existing_user:
                secret = secrets.token_urlsafe(48)
                newPWD = self._hash_password(secret)
                # Create user if it doesn't exist
                logger.info(f"Creating new user for {username} after successful login.")
                existing_user = User(email=email, password_hash=newPWD, id=_id)
                await self.user_storage.save_user(existing_user)
            return existing_user

        except Exception as e:
            logger.error(f"Token introspection failed: {e}")
            raise UnauthorizedException("Token is invalid")


    def _introspect_token(self, token) -> dict | None:
        headers = {
            "Authorization": self.auth_header,
            "User-Agent": "curl/8.7.1",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"token": token}

        response = requests.post(EGI_CHECKIN_INTROSPECTION_ENDPOINT, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        return response.json()


class AuthServiceProvider(Provider):

    def __init__(self, *args, **kwargs):
        super().__init__(scope=Scope.REQUEST, *args, **kwargs)
        if USE_EGI_CHECKIN_AUTH:
            logger.info("Using EGI Check-in authentication")
            if not EGI_CHECKIN_INTROSPECTION_ENDPOINT or not EGI_CHECKIN_CLIENT_ID or not EGI_CHECKIN_CLIENT_SECRET:
                logger.warning("EGI Check-in authentication is enabled but some required settings are missing. Please check your configuration.")

    @provide
    def provide_auth_service(
        self,
        user_service: UserStorageService,
        request: Request
    ) -> AuthService:
        return (
            JWTAuthService(user_storage=user_service, request=request)
            if not USE_EGI_CHECKIN_AUTH
            else EGIAuthService(user_service, request)
        )
