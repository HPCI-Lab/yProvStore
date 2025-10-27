import logging
import asyncio
from typing import AsyncGenerator
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession as SessionType
from dishka import Provider, provide, Scope

from services.db.sql.base import AsyncSessionLocal, engine
from alembic.config import Config
from alembic.script import ScriptDirectory

logger = logging.getLogger(__name__)


class DBServiceProvider(Provider):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        asyncio.run(self._check_database_migrations())

    async def _check_database_migrations(self):
        """Check database migrations asynchronously"""
        async with engine.connect() as conn:
            # Check if database has tables
            inspector = await conn.run_sync(lambda sync_conn: inspect(sync_conn))
            table_names = await conn.run_sync(lambda sync_conn: inspector.get_table_names())
            
            if not table_names:
                logger.error("Database is empty (no tables).")
                raise Exception("Database is empty (no tables). You can run database migrations with: `uv run alembic upgrade head`.")

        try:
            cfg = Config("alembic.ini")
            script = ScriptDirectory.from_config(cfg)
            heads = set(script.get_heads())

            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT version_num FROM alembic_version"))
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
                raise Exception("Database migrations are not up-to-date. You can run database migrations with: `uv run alembic upgrade head`.")
            logger.info("Database migrations are up-to-date.")
        except FileNotFoundError:
            logger.warning("alembic.ini not found, skipping migration check.")

    @provide(scope=Scope.REQUEST)
    async def get_db_session(self) -> AsyncGenerator[SessionType, None]:
        session = AsyncSessionLocal()
        try:
            yield session
        finally:
            await session.close()
