import logging

from pydantic import BaseModel, Field
from fastapi import APIRouter, status
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.settings import PID_PREFIX
from application.documentation.openapi_generation import EXAMPLE_EMAIL
from application.exceptions.types import ForbiddenException
from routers.common.dependencies import LoggedUser
from routers.common.schemas import SuccessResponse
from services.permission_storage.service import DocumentPermissionStorageService
from services.document_storage.service import DocumentRecordStorageService


__all__ = ("router",)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="",
    route_class=DishkaRoute
)


class DeletePermissionRequest(BaseModel):
    """
    Request model for deleting a document permission.
    """
    user_email: str = Field(..., example=EXAMPLE_EMAIL, description="Email of the user whose permission is to be deleted.")


documentation = {
    "summary": "Delete Document Permissions",
    "description": ("This endpoint deletes a specific permission associated with a document pid and a user.\n"
                    "The first document version PID is used to find and delete the permission."),
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns a success message if the permission is deleted."
}


@router.delete("/{prefix}/{pid}/permissions", **documentation)
async def delete_permission_prefix(
    pid: str,
    prefix: str,
    data: DeletePermissionRequest,
    permission_storage: FromDishka[DocumentPermissionStorageService],
    document_record_storage: FromDishka[DocumentRecordStorageService],
    logged_user: LoggedUser
) -> SuccessResponse:
    """
    Delete a specific permission for a document identified by its PID and a user email.
    The first document version is used to find and delete the permission.
    """
    pid = f"{prefix}/{pid}"
    document_record = await document_record_storage.get_document_by_pid(pid)
    first_document_record = await permission_storage.get_first_document_record(document_record)

    # Validate the logged user has permission to delete
    if first_document_record.owner_id != logged_user.id:
        raise ForbiddenException("You do not have permission to manage access for this document.")

    await permission_storage.delete_permission(first_document_record.pid, data.user_email)
    return SuccessResponse(message="Permission deleted successfully.")


documentation.update({
    "description": "This endpoint deletes a specific permission associated with a document pid and a user. PID prefix is set by default to the application PID prefix."
})


@router.delete("/{pid}/permissions", **documentation)
async def delete_permission(
    pid: str,
    data: DeletePermissionRequest,
    permission_storage: FromDishka[DocumentPermissionStorageService],
    document_record_storage: FromDishka[DocumentRecordStorageService],
    logged_user: LoggedUser
) -> SuccessResponse:
    """
    Delete a specific permission for a document identified by its PID and a user email.
    The first document version is used to find and delete the permission.
    """
    return await delete_permission_prefix(
        pid=pid,
        prefix=PID_PREFIX,
        data=data,
        permission_storage=permission_storage,
        document_record_storage=document_record_storage,
        logged_user=logged_user
    )
