from fastapi import APIRouter

from ._get import router as get_router
from ._update import router as update_router
from ._schema import router as schema_router


metadata_router = APIRouter(
    prefix="/documents",
    tags=["Provenance Documents Metadata"],
)


# Include the sub-routers for metadata operations
metadata_router.include_router(get_router)
metadata_router.include_router(update_router)


metadata_schema_router = APIRouter(
    prefix="",
    tags=["Provenance Documents Metadata"],
)


metadata_schema_router.include_router(schema_router)
