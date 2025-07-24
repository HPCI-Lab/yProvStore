import abc
import uuid
import logging
from typing import Any

from sqlalchemy import asc, desc, select

from application.exceptions.types import NotFoundException, ConflictException
from services.db.sql.base import BaseDBModel

logger = logging.getLogger(__name__)


class AbstractEntityDB[T: BaseDBModel](abc.ABC):
    """
    Abstract base class for a database that manages crud operations for entities.
    """

    @abc.abstractmethod
    async def _create(self, entity: T) -> T:
        """
        Create a new entity in the database.
        """
        pass

    @abc.abstractmethod
    async def _get(self, entity_id: str, raise_not_found: bool = True) -> T | None:
        """
        Get an entity from the database by its ID.
        """
        pass

    @abc.abstractmethod
    async def _filter(self, **kwargs) -> list[T]:
        """
        Filter entities based on provided keyword arguments.
        This method should return a list of entities that match the filter criteria.
        """
        pass

    @abc.abstractmethod
    async def _update(self, entity: T) -> T:
        """
        Update an existing entity in the database.
        """
        pass

    @abc.abstractmethod
    async def delete(self, entity_id: str) -> None:
        """
        Delete an entity from the database by its ID.
        """
        pass


class SQLEntityDB[T: BaseDBModel](AbstractEntityDB[T]):
    """
    SQL database interface for managing entities.
    This class should be implemented with specific SQL operations.
    """

    def __class_getitem__(cls, item):
        if not issubclass(item, T.__bound__):
            raise TypeError(f"Cannot initialize {cls}, {item} is not a subclass of {T.__bound__}")
        # cls._model_type = item
        return cls

    def __init__(self, session, model_type: type[T]):
        """
        Initialize the SQL database with a session.
        :param session: SQLAlchemy session object
        """
        self.session = session
        self._model_type = model_type

    async def _create(self, entity: T) -> T:
        """
        Create a new entity in the SQL database.
        """
        self._validate_entity(entity)
        if hasattr(entity, 'id') and entity.id is not None:
            existing_entity = self.session.query(self._model_type).filter_by(id=entity.id).first()
            if existing_entity:
                raise ConflictException(f"{self._model_type.model_name()} with ID '{entity.id}' already exists.")
        if not hasattr(entity, 'id') or entity.id is None:
            entity.id = str(uuid.uuid4())
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    async def _get(self, entity_id: str, raise_not_found: bool = True) -> T | None:
        """
        Get an entity from the SQL database by its ID.
        """
        entity = self.session.query(self._model_type).filter_by(id=entity_id).first()
        if not entity or (hasattr(entity, 'deleted') and entity.deleted):
            if raise_not_found:
                raise NotFoundException(f"{self._model_type.model_name()} with ID '{entity_id}' not found.")
            return None
        return entity

    async def _filter(
        self,
        limit: int | None = None,
        order_by: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        **kwargs
    ) -> list[T]:
        """
        Filter entities in the SQL database based on provided keyword arguments.
        Supports pagination with zero-indexed pages and page_size.
        """
        conditions = []
        if hasattr(self._model_type, 'deleted'):
            kwargs.update({"deleted": False})  # Ensure we filter out soft-deleted entities
        try:
            for key, value in kwargs.items():
                nested = key.split("__")
                if len(nested) == 1:
                    conditions.append(getattr(self._model_type, key) == value)
                elif len(nested) > 2:
                    raise NotImplementedError("Nested filtering with foreign keys is not implemented yet.")
                elif len(nested) == 2:
                    condition = self._generate_filter_condition(nested[0], nested[1], value, self._model_type)
                    if condition is not None:
                        conditions.append(condition)
        except AttributeError as e:
            logger.error(f"AttributeError in filtering [{self._model_type.__name__}] with kwargs [{kwargs}]: {e}")
            return []

        statement = select(self._model_type).filter(*conditions)

        # Pagination logic
        if page is not None and page_size is not None:
            if page < 0 or page_size <= 0:
                raise ValueError("Page must be >= 0 and page_size must be > 0")
            statement = statement.offset(page * page_size).limit(page_size)
        elif limit:
            statement = statement.limit(limit)

        if order_by:
            order = order_by.split(" ")
            order_function = asc
            if len(order) == 2:
                if order[1].lower() == "desc":
                    order_function = desc
                elif order[1].lower() == "asc":
                    order_function = asc
                else:
                    raise Exception(f"Unsupported order_by [{order_by}] for filtering [{self._model_type.__name__}]")
            elif len(order) != 1:
                raise Exception(f"Unsupported order_by [{order_by}] for filtering [{self._model_type.__name__}]")
            if not hasattr(self._model_type, order[0]):
                raise AttributeError(f"Attribute [{order[0]}] not found in model [{self._model_type.__name__}].")
            statement = statement.order_by(order_function(getattr(self._model_type, order[0])))

        return self.session.scalars(statement).all()

    async def _update(self, entity: T) -> T:
        """
        Update an existing entity in the SQL database.
        """
        self._validate_entity(entity)
        existing_entity = await self._get(entity.id)
        for key, value in entity.__dict__.items():
            setattr(existing_entity, key, value)
        self.session.commit()
        self.session.refresh(existing_entity)
        return existing_entity

    async def delete(self, entity_id: str, soft_delete: bool = True) -> None:
        """
        Delete an entity from the SQL database by its ID.
        """
        entity = await self._get(entity_id)
        if hasattr(entity, 'deleted') and soft_delete:
            entity.deleted = True
            self.session.commit()
            self.session.refresh(entity)
        else:
            self.session.delete(entity)
        self.session.commit()

    def _validate_entity(self, entity: T) -> None:
        """
        Validate the entity before performing operations.
        This method can be overridden in subclasses for additional validation.
        """
        if not isinstance(entity, self._model_type):
            raise TypeError(f"Expected entity of type {self._model_type.__name__}, got {type(entity)}")

    def _generate_filter_condition(self, parent_value, nested_value, value, parent_class) -> Any:
        # if hasattr(parent_class, parent_value):
        #     try:
        #         return getattr(parent_class, parent_value) == value
        #     except AttributeError as e:
        #         logger.error(f"AttributeError [{parent_value}] in generating filter condition for [{self._model_type.__name__}]: {e}")
        #         return None
        supported_operations = ["eq", "ne", "lt", "le", "gt", "ge", "in", "like", "ilike", "is_null", "is_not_null"]
        print(f"Generating filter condition for [{self._model_type.__name__}] with parent_value [{parent_value}] and nested_value [{nested_value}]")
        if nested_value in supported_operations:
            try:
                operations = {
                    "eq": (lambda: getattr(parent_class, parent_value) == value),
                    "ne": (lambda: getattr(parent_class, parent_value) != value),
                    "lt": (lambda: getattr(parent_class, parent_value) < value),
                    "le": (lambda: getattr(parent_class, parent_value) <= value),
                    "gt": (lambda: getattr(parent_class, parent_value) > value),
                    "ge": (lambda: getattr(parent_class, parent_value) >= value),
                    "in": (lambda: getattr(parent_class, parent_value).in_(value)),
                    "like": (lambda: getattr(parent_class, parent_value).like(value)),
                    "ilike": (lambda: getattr(parent_class, parent_value).ilike(value)),
                    "is_null": (lambda: getattr(parent_class, parent_value).is_(None) if value else getattr(parent_class, parent_value).isnot(None)),
                    "is_not_null": (lambda: getattr(parent_class, parent_value).isnot(None) if value else getattr(parent_class, parent_value).is_(None)),
                }
            except AttributeError as e:
                logger.error(f"AttributeError [{parent_value}__{nested_value}] in generating filter condition for [{self._model_type.__name__}]: {e}")
                return None
            return operations[nested_value]()
        else:
            raise NotImplementedError(f"Unsupported operation [{parent_value}__{nested_value}] for filtering [{self._model_type.__name__}]")
