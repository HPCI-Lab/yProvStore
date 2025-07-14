from dishka import Provider, provide, Scope
from sqlalchemy.orm import Session as SessionType

from application.exceptions.types import ConflictException, NotFoundException
from models import User
from services.db.sql.models import DBUser
from services.db.sql.crud import SQLEntityDB


class UserStorageService:
    """
    Interface for user storage operations.
    """

    async def get_user_by_email(self, email: str) -> User:
        """
        Retrieve a user by their email address.
        """
        raise NotImplementedError

    async def get_user_by_id(self, user_id: str) -> User:
        """
        Retrieve a user by their unique ID.
        """
        raise NotImplementedError

    async def save_user(self, user: User) -> None:
        """
        Save a new user to the storage.
        """
        raise NotImplementedError

    async def get_user_emails(self, ids: list[str]) -> dict[str, str]:
        """
        Retrieve emails of users by their ids.

        :param ids: List of user IDs to retrieve emails for.
        :return: Dictionary mapping user IDs to their emails.
        """
        raise NotImplementedError


class UserStorageServiceImpl(UserStorageService, SQLEntityDB[DBUser]):
    """
    Concrete implementation of UserStorageService that interacts with a database.
    """

    def __init__(self, session: SessionType):
        super().__init__(session, model_type=DBUser)

    async def get_user_by_email(self, email: str, raise_not_found: bool = True) -> User:
        users = await self._filter(email=email)
        if len(users) > 1:
            raise ConflictException(f"Multiple users found with email '{email}'")
        elif len(users) == 0:
            if raise_not_found:
                raise NotFoundException(f"User with email '{email}' not found")
            return None
        return users[0].to_user()

    async def get_user_by_id(self, user_id: str) -> User:
        return await super()._get(user_id)

    async def save_user(self, user: User) -> None:
        db_user = DBUser.from_user(user)
        new_db_user = await super()._create(db_user)
        return new_db_user.to_user()

    async def get_user_emails(self, ids: list[str]) -> list[tuple[str, str]]:
        users = await super()._filter(id__in=ids)
        return {user.id: user.email for user in users}


class UserStorageProvider(Provider):

    user_storage_service = provide(source=UserStorageServiceImpl, scope=Scope.REQUEST, provides=UserStorageService)
