from fastapi import APIRouter, status

from application.exceptions.responses import EXCEPTION_SCHEMA
from application.exceptions.types import UnauthorizedException, ForbiddenException, NotFoundException

from ._list import router as list_router
from ._create import router as create_router
from ._delete import router as delete_router

__all__ = ("router",)


router = APIRouter(
    prefix="/documents",
    tags=["Document Permissions"],
    responses={
        status.HTTP_401_UNAUTHORIZED: EXCEPTION_SCHEMA[UnauthorizedException],
        status.HTTP_403_FORBIDDEN: EXCEPTION_SCHEMA[ForbiddenException, "You do not have permission to manage access for this document."],
        status.HTTP_404_NOT_FOUND: EXCEPTION_SCHEMA[NotFoundException, "The specified document PID does not exist."]
    }
)

# Include the sub-routers for managing document permissions
router.include_router(list_router)
router.include_router(create_router)
router.include_router(delete_router)
