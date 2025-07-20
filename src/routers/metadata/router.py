from fastapi import APIRouter

from ._get import router as get_router
from ._update import router as update_router


pids_router = APIRouter(
    prefix="/documents",
    tags=["Provenance Documents Metadata"],
)


# Include the sub-routers for listing and creating documents
pids_router.include_router(get_router)
pids_router.include_router(update_router)
