from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from dishka.integrations.fastapi import DishkaRoute

from routers.authentication.router import router as authentication_router
from routers.documents.router import documents_router
from routers.documents.router import document_router
# from routers.permissions.router import router as permissions_router

__all__ = ('root_router',)


root_router = APIRouter(route_class=DishkaRoute)


@root_router.get("/", tags=["General"])
async def redirect_to_docs() -> RedirectResponse:
    return RedirectResponse(url="docs/")


root_sub_routers: tuple[APIRouter, ...] = (
    authentication_router,
    documents_router,
    document_router,
    # permissions_router,
)

for router in root_sub_routers:
    root_router.include_router(router)
