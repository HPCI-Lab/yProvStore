import logging

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from models import DocumentPermission, PermissionLevel
from routers.common.dependencies import LoggedUser
from routers.permissions._list import DocumentPermissionGet
from services.permission_storage.service import DocumentPermissionStorageService
from services.document_storage.service import DocumentRecordStorageService
from services.user_storage.service import UserStorageService
from application.exceptions.responses import EXCEPTION_SCHEMA
from application.exceptions.types import ForbiddenException, BadRequestException, ConflictException, NotFoundException
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
    user_email: str = Field(..., examples=[EXAMPLE_EMAIL], description="Email of the user to whom the permission is granted.")
    permission_level: PermissionLevel = Field(..., examples=[PermissionLevel.WRITE], description="The level of permission to be granted to the user.")


documentation = {
    "summary": "Create Document Permission",
    "description": ("This endpoint allows the creation of a new permission for a specific document and user.\n"
                    "At the moment, only the WRITE permission is supported, as READ permissions are automatically granted to all users.\n"
                    "Only the owner of the document can manage permissions for it.\n\n"
                    "!! NOTE: Permissions on documents are treated the same for documents of the same lineage (permissions are always set on the first version of the document)."),
    "status_code": status.HTTP_201_CREATED,
    "response_description": "Returns the created document permission.",
    "responses": {
        status.HTTP_400_BAD_REQUEST: EXCEPTION_SCHEMA[BadRequestException, "Invalid request data or permission type."],
        status.HTTP_409_CONFLICT: EXCEPTION_SCHEMA[ConflictException, "A permission already exists for this user on the document."]
    },
}


@router.post("", **documentation)
async def create_permission(
    pid: str,
    request: CreatePermissionRequest,
    permission_storage: FromDishka[DocumentPermissionStorageService],
    document_record_storage: FromDishka[DocumentRecordStorageService],
    user_storage: FromDishka[UserStorageService],
    logged_user: LoggedUser
) -> DocumentPermissionGet:
    """
    The passed PID must be of the form `<prefix>/<pid>`, where `<prefix>` is the PID prefix and `<pid>` is the document PID.
    Create a new permission for a specific document and user.
    The permission document PID is determined by the first version of the document in its lineage.
    Only the owner of the first version of the document can manage permissions.
    """
    document_record = await document_record_storage.get_document_by_pid(pid)
    
    if request.permission_level != PermissionLevel.WRITE:
        raise BadRequestException("Currently, only WRITE permissions can be created. READ permissions are automatically granted to all users.")
    
    first_document_record = await permission_storage.get_first_document_record(document_record)
    
    # Only owner of the first document can manage permissions
    if first_document_record.owner_id != logged_user.id:
        raise ForbiddenException("You do not have permission to manage this document. You must be the owner of the first version document to create permissions.")

    user = await user_storage.get_user_by_email(request.user_email)
    if first_document_record.owner_id == user.id:
        raise BadRequestException("You cannot create a permission for yourself as the owner of the first version document.")

    new_permission = DocumentPermission(
        pid=first_document_record.pid,
        user_id=user.id,
        permission_level=request.permission_level
    )
    # Create and return the new permission for the specified document PID
    try:
        permission = await permission_storage.save_permission(new_permission)
        return DocumentPermissionGet(
            pid=permission.pid,
            user_email=user.email,
            permission_level=permission.permission_level
        )
    except ConflictException as e:
        raise ConflictException(f"Permission for user '{user.email}' on document '{first_document_record.pid}' already exists.") from e
