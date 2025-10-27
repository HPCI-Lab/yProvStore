import asyncio
import logging

from sqlalchemy import DateTime, Column, func, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from application.settings import DB_CONNECTION_STRING


Base = declarative_base()

# Set up the database engine
connect_args = {}
if DB_CONNECTION_STRING.startswith("postgresql"):
    connect_args = {
        # set server-level options on each new connection
        "server_settings": {
            "application_name": "yprovstore-api",
            # "statement_timeout": "5000",   # in ms as string
        }
    },
engine = create_async_engine(
    DB_CONNECTION_STRING,
    poolclass=NullPool,
    echo=False,
    connect_args=connect_args
)

logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# Create all tables
# Base.metadata.create_all(engine)
# -> https://stackoverflow.com/a/74000761
# async def init_models():
#     """Creates tables if they don't exist"""
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)

# asyncio.run(init_models())

# Set up session
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


class BaseDBModel(Base):
    """
    Base model class for SQLAlchemy ORM.
    All models should inherit from this class.
    """
    __abstract__ = True

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted = Column('deleted', Boolean, default=False, nullable=False)

    @classmethod
    def model_name(cls) -> str:
        """
        Return the name of the model.
        This is used for logging and response formatting.
        """
        return cls.__name__
