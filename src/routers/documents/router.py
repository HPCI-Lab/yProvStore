from fastapi import APIRouter

from ._list import router as list_router
from ._create import router as create_router
from ._get import router as get_router
from ._download import router as download_router

__all__ = ("documents_router", "document_router")


documents_router = APIRouter(
    prefix="",
    tags=["Provenance Documents"],
)


# Include the sub-routers for listing and creating documents
documents_router.include_router(list_router)
documents_router.include_router(create_router)



# TODO: add to documentation that prefix is not passed (or endpoints fail)
#       !! OR CREATE A NEW ROUTER FOR DOCUMENTS WITH PREFIX !!


document_router = APIRouter(
    prefix="/documents",
    tags=["Provenance Documents"],
)


# Include the sub-routers for retrieving a document
document_router.include_router(get_router)
document_router.include_router(download_router)
