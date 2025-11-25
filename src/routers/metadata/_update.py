import logging
from datetime import datetime, timezone

from fastapi import status, APIRouter
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.exceptions.responses import EXCEPTION_SCHEMA
from application.exceptions.types import NotFoundException, ServiceUnavailableException
from services.document_storage.service import DocumentRecordStorageService
from services.metadata.service import DocumentMetadataService
from services.permission_storage.service import DocumentPermissionStorageService
from services.file_storage.service import FileStorageService
from models import PermissionLevel
from routers.common.dependencies import LoggedUser

from ._get import DocumentMetadataGet
from .utils import DocumentMetadataPost, update_document_metadata

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="",
    route_class=DishkaRoute
)


documentation = {
    "summary": "Update Document Metadata",
    "description": ("This endpoint updates metadata for a specific document by its PID."
                    "Only the fields that are provided in the request body will be updated.\n"
                    "To set an empty field, use an empty string or an empty list."),
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns the updated document metadata including title, description, and keywords.",
    "responses": {
        status.HTTP_404_NOT_FOUND: EXCEPTION_SCHEMA[NotFoundException, "The specified document PID does not exist."],
        status.HTTP_503_SERVICE_UNAVAILABLE: EXCEPTION_SCHEMA[ServiceUnavailableException]
    }
}


@router.patch("/{pid:path}/metadata", **documentation)
async def update_metadata(
    pid: str,
    document_metadata: DocumentMetadataPost,
    document_record_storage: FromDishka[DocumentRecordStorageService],
    permission_storage: FromDishka[DocumentPermissionStorageService],
    metadata_service: FromDishka[DocumentMetadataService],
    file_storage_service: FromDishka[FileStorageService],
    logged_user: LoggedUser
) -> DocumentMetadataGet:
    """
    Endpoint to retrieve metadata for a specific document by its PID.
    """

    # Fetch the document record by PID to verify it is handled by this server instance
    document_record = await document_record_storage.get_document_by_pid(pid)

    # Verify the user has permission to update the document
    await permission_storage.validate_user_permission(logged_user, document_record, permission_level=PermissionLevel.WRITE)

    # Update the document metadata
    metadata = await update_document_metadata(
        pid,
        document_metadata,
        metadata_service,
        document_record_storage,
        file_storage_service
    )

    return DocumentMetadataGet.from_metadata(metadata)
