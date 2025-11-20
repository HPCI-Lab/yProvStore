from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from dishka.integrations.fastapi import DishkaRoute

from routers.authentication.router import router as authentication_router
from routers.documents.router import documents_router, document_router
from routers.pids.router import pids_router, pid_router
from routers.permissions.router import router as permissions_router
from routers.metadata.router import metadata_router, metadata_schema_router
from routers.graph.router import router as graph_router

__all__ = ('root_router',)


root_router = APIRouter(route_class=DishkaRoute)


@root_router.get("/", tags=["General"])
async def redirect_to_docs() -> RedirectResponse:
    return RedirectResponse(url="docs/")


@root_router.get("/status", tags=["General"], summary="Get API Status", description="Returns the current status of the API.",
                 responses={200: {"description": "Successful Response", "content": {"application/json": {"example": {"status": "ok"}}}}})
async def status() -> dict[str, str]:
    """
    Returns the status of the API.
    """
    return {"status": "ok"}


root_sub_routers: tuple[APIRouter, ...] = (
    authentication_router,
    documents_router,
    metadata_router,
    document_router,
    permissions_router,
    pids_router,
    pid_router,
    metadata_schema_router,
    graph_router
)

for router in root_sub_routers:
    root_router.include_router(router)
