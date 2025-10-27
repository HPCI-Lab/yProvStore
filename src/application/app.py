from typing import AsyncIterator

from fastapi import FastAPI
from dishka import make_async_container
from contextlib import asynccontextmanager
from fastapi.responses import ORJSONResponse
from dishka.integrations.fastapi import setup_dishka

from services import providers
from routers import root_router
from middlewares import middlewares
from application.exceptions.handler import handle_exception
from application.logging_config.config import configure_logging
from application.documentation.openapi_generation import custom_openapi


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.dishka_container.close()  # type: ignore


def get_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
    )
    app.include_router(root_router)
    for middleware in middlewares:
        app.add_middleware(middleware)
    app.add_exception_handler(Exception, handle_exception)

    app.openapi = lambda: custom_openapi(app)

    services = [provider() for provider in providers]
    container = make_async_container(*services)
    setup_dishka(container=container, app=app)

    return app
