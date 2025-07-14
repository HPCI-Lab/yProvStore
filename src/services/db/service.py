import logging
from typing import Iterable
from sqlalchemy import inspect
from sqlalchemy.orm import Session as SessionType
from dishka import Provider, provide, Scope

from services.db.sql.base import Session, engine

logger = logging.getLogger(__name__)


class DBServiceProvider(Provider):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inspector = inspect(engine)
        if not inspector.get_table_names():
            logger.error("Database is empty (no tables).")
            raise Exception("Database is empty (no tables), verify your configuration and migrations.")

    @provide(scope=Scope.REQUEST)
    def get_db_session(self) -> Iterable[SessionType]:
        session = Session()
        try:
            yield session
        finally:
            session.close()
