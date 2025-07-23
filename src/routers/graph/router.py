from fastapi import APIRouter

from ._list import router as list_router
from ._subgraph import router as subgraph_router


router = APIRouter(
    prefix="/documents/{prefix}/{pid}/graph",
    tags=["Provenance Documents Graph Operations"],
)


# Include the sub-routers for listing and subgraph operations
router.include_router(list_router)
router.include_router(subgraph_router)
