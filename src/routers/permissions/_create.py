import logging

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from models import DocumentPermission, PermissionLevel
from routers.common.dependencies import LoggedUser
from services.permission_storage.service import DocumentPermissionStorageService
from services.document_storage.service import DocumentRecordStorageService
from services.user_storage.service import UserStorageService
from application.exceptions.responses import EXCEPTION_SCHEMA
from application.exceptions.types import ForbiddenException, BadRequestException, ConflictException
from application.documentation.openapi_generation import EXAMPLE_EMAIL


__all__ = ("router",)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/permissions",
    route_class=DishkaRoute
)


class CreatePermissionRequest(BaseModel):
    """
    Request model for creating a new document permission.
    """
    user_email: str = Field(..., example=EXAMPLE_EMAIL, description="Email of the user to whom the permission is granted.")
    permission_level: PermissionLevel = Field(..., example=PermissionLevel.READ, description="The level of permission to be granted to the user.")


documentation = {
    "summary": "Create Document Permission",
    "description": "This endpoint allows the creation of a new permission for a specific document and user.",
    "status_code": status.HTTP_201_CREATED,
    "response_description": "Returns the created document permission.",
    "responses": {
        status.HTTP_400_BAD_REQUEST: EXCEPTION_SCHEMA[BadRequestException, "Invalid request data or permission type."],
        status.HTTP_409_CONFLICT: EXCEPTION_SCHEMA[ConflictException, "A permission already exists for this user on the document."]
    }
}


@router.post("", **documentation)
async def create_permission(
    pid: str,
    request: CreatePermissionRequest,
    permission_storage: FromDishka[DocumentPermissionStorageService],
    document_record_storage: FromDishka[DocumentRecordStorageService],
    user_storage: FromDishka[UserStorageService],
    logged_user: LoggedUser
) -> DocumentPermission:
    """
    Create a new permission for a specific document and user.
    """
    document_record = await document_record_storage.get_document_by_pid(pid)

    # TODO: unify permissions of documents of same lineage

    # Only owner of the document can manage permissions
    if document_record.owner_id != logged_user.id:
        raise ForbiddenException("You do not have permission to manage permissions for this document.")

    user = await user_storage.get_user_by_email(request.user_email)
    if document_record.owner_id == user.id:
        raise BadRequestException("You cannot create a permission for yourself as the owner of the document.")

    new_permission = DocumentPermission(
        pid=pid,
        user_id=user.id,
        permission_level=request.permission_level
    )
    # Create and return the new permission for the specified document PID
    try:
        return await permission_storage.save_permission(new_permission)
    except ConflictException as e:
        raise ConflictException(f"Permission for user '{user.email}' on document '{pid}' already exists.") from e
