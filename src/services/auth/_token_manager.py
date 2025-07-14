import jwt
from datetime import datetime, timedelta, timezone
from dataclasses import asdict

from application.exceptions.types import UnauthorizedException
from application.settings import JWT_ENCODING_ALGORITHM, JWT_SECRET_KEY, JWT_EXPIRATION_MINUTES
from models import TokenData


class TokenManager:

    @staticmethod
    def create_access_token(data: TokenData, expires_delta: timedelta | None = None) -> str:
        to_encode = asdict(data)
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ENCODING_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> TokenData:
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ENCODING_ALGORITHM])
            return TokenData.from_dict(payload)
        except jwt.ExpiredSignatureError:
            raise UnauthorizedException("Token has expired.")
        except jwt.InvalidTokenError:
            raise UnauthorizedException("Invalid token.")
