import logging

from sqlalchemy import create_engine, DateTime, Column, func, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

from application.settings import DB_CONNECTION_STRING, DB_MAX_POOL_SIZE, DB_MAX_OVERFLOW, DB_TIMEOUT


Base = declarative_base()

engine = create_engine(DB_CONNECTION_STRING, echo=False, pool_size=DB_MAX_POOL_SIZE, max_overflow=DB_MAX_OVERFLOW, pool_timeout=DB_TIMEOUT)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# Create all tables
Base.metadata.create_all(engine)

# Set up session
Session = sessionmaker(bind=engine)


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
