from fastapi import APIRouter

from ._list import router as list_router
from ._download_url import router as download_router
from ._proxy_upload import router as upload_router
from ._upload_url import router as upload_url_router
from ._download_url import router as download_url_router

__all__ = ("artifacts_router", "artifact_router")


artifacts_router = APIRouter(
    prefix="",
    tags=["Artifacts"],
)


# Include the sub-routers for listing and creating artifacts
artifacts_router.include_router(list_router)


upload_download_router = APIRouter(
    prefix="/artifacts",
)

# Include the sub-routers for uploading artifacts
upload_download_router.include_router(upload_router)
upload_download_router.include_router(upload_url_router)
# Include the sub-routers for downloading artifacts
upload_download_router.include_router(download_router)
upload_download_router.include_router(download_url_router)


# Include the sub-routers for retrieving a artifact
artifacts_router.include_router(upload_download_router)
