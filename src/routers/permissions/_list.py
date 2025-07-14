import logging

from pydantic import BaseModel, Field
from fastapi import APIRouter, status
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.exceptions.types import ForbiddenException
from application.documentation.openapi_generation import EXAMPLE_UUID, EXAMPLE_EMAIL
from models import PermissionLevel
from routers.common.dependencies import LoggedUser
from services.permission_storage.service import DocumentPermissionStorageService
from services.user_storage.service import UserStorageService
from services.document_storage.service import DocumentRecordStorageService


__all__ = ("router",)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/permissions",
    route_class=DishkaRoute
)


class DocumentPermissionGet(BaseModel):
    pid: str = Field(..., example=EXAMPLE_UUID, description="The pid of the document.")
    user_email: str = Field(..., example=EXAMPLE_EMAIL, description="Email of the user who has the permission.")
    permission_level: PermissionLevel


documentation = {
    "summary": "List Document Permissions",
    "description": "This endpoint retrieves a list of all permissions associated with a specific document.",
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns a list of permissions for the specified document."
}


@router.get("", **documentation)
async def list_permissions(
    pid: str,
    permission_storage: FromDishka[DocumentPermissionStorageService],
    document_record_storage: FromDishka[DocumentRecordStorageService],
    user_storage: FromDishka[UserStorageService],
    logged_user: LoggedUser
) -> list[DocumentPermissionGet]:
    """
    List all permissions for a specific document.
    """
    document_record = await document_record_storage.get_document_by_pid(pid)

    # Only owner of the document can manage permissions
    if document_record.owner_id != logged_user.id:
        raise ForbiddenException("You do not have permission to manage permissions for this document.")

    # Fetch and return the list of permissions for the specified document PID
    perms = await permission_storage.list_permissions_for_doc(pid)

    user_emails = await user_storage.get_user_emails([perm.user_id for perm in perms])
    return [DocumentPermissionGet(
        pid=perm.pid,
        user_email=user_emails[perm.user_id],
        permission_level=perm.permission_level
    ) for perm in perms]
