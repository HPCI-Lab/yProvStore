import logging
from typing import Iterable
from sqlalchemy import inspect
from sqlalchemy.orm import Session as SessionType
from dishka import Provider, provide, Scope

from services.db.sql.base import Session, engine
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

logger = logging.getLogger(__name__)


class DBServiceProvider(Provider):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inspector = inspect(engine)
        if not inspector.get_table_names():
            logger.error("Database is empty (no tables).")
            raise Exception("Database is empty (no tables), verify your configuration and migrations.")

        try:
            cfg = Config("alembic.ini")
            script = ScriptDirectory.from_config(cfg)
            heads = set(script.get_heads())

            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                db_revs = {row[0] for row in result.fetchall()}

            if not db_revs:
                logger.error("alembic_version table is empty or missing.")
                raise Exception("Migrations not applied: alembic_version table is empty.")

            # If any DB revision is not among the current migration heads, migrations are missing/outdated.
            if not db_revs.issubset(heads):
                logger.error(
                "Database migrations are not up-to-date. DB revisions: %s; Expected heads: %s",
                sorted(db_revs), sorted(heads)
                )
                raise Exception("Database migrations are not up-to-date; run your migrations with: `uv run alembic upgrade head`.")
            logger.info("Database migrations are up-to-date.")
        except FileNotFoundError:
            logger.warning("alembic.ini not found, skipping migration check.")

    @provide(scope=Scope.REQUEST)
    def get_db_session(self) -> Iterable[SessionType]:
        session = Session()
        try:
            yield session
        finally:
            session.close()
