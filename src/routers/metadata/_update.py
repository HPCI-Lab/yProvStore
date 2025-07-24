import logging
from datetime import datetime

from fastapi import status, APIRouter
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.exceptions.responses import EXCEPTION_SCHEMA
from application.exceptions.types import NotFoundException, ServiceUnavailableException
from services.document_storage.service import DocumentRecordStorageService
from services.metadata.service import DocumentMetadataService
from services.permission_storage.service import DocumentPermissionStorageService
from models import PermissionLevel
from routers.common.dependencies import LoggedUser
from ._get import DocumentMetadataGet

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="",
    route_class=DishkaRoute
)


class DocumentMetadataPost(DocumentMetadataGet):
    """
    Request model for updating document metadata.
    """
    pass


documentation = {
    "summary": "Update Document Metadata",
    "description": ("This endpoint updates metadata for a specific document by its PID and prefix."
                    "Only the fields that are provided in the request body will be updated.\n"
                    "To set an empty field, use an empty string or an empty list."),
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns the updated document metadata including title, description, and keywords.",
    "responses": {
        status.HTTP_404_NOT_FOUND: EXCEPTION_SCHEMA[NotFoundException, "The specified document PID does not exist."],
        status.HTTP_503_SERVICE_UNAVAILABLE: EXCEPTION_SCHEMA[ServiceUnavailableException]
    }
}


@router.patch("/{prefix}/{pid}/metadata", **documentation)
async def update_metadata_prefix(
    prefix: str,
    pid: str,
    document_metadata: DocumentMetadataPost,
    document_record_storage: FromDishka[DocumentRecordStorageService],
    permission_storage: FromDishka[DocumentPermissionStorageService],
    metadata_service: FromDishka[DocumentMetadataService],
    logged_user: LoggedUser
) -> DocumentMetadataGet:
    """
    Endpoint to retrieve metadata for a specific document by its PID and prefix.
    """

    pid = f"{prefix}/{pid}"
    # Fetch the document record by PID to verify it is handled by this server instance
    document_record = await document_record_storage.get_document_by_pid(pid)

    # Verify the user has permission to update the document
    await permission_storage.validate_user_permission(logged_user, document_record, permission_level=PermissionLevel.WRITE)

    metadata = await metadata_service.get_document_metadata(pid)

    # Update the metadata with the provided fields
    for field, value in document_metadata.model_dump().items():
        if value is not None:
            setattr(metadata, field, value)

    # Save the updated metadata
    metadata = await metadata_service.update_document_metadata(pid, metadata)

    # Set `updated_at` to current time for document record
    try:
        await document_record_storage.document_is_updated(pid, datetime.now())
    except Exception as e:
        logger.warning(f"Failed to update document record `updated_at` for PID '{pid}': {e}")

    return DocumentMetadataGet.from_metadata(metadata)


# documentation.update({
#     "description": ("This endpoint updates a specific document metadata by its PID. "
#                     "Prefix is set by default to the application PID prefix.\n"
#                     "Only the fields that are provided in the request body will be updated.\n"
#                     "To set an empty field, use an empty string or an empty list.")
# })


# @router.patch("/{pid}/metadata", **documentation)
# async def update_metadata(
#     pid: str,
#     document_metadata: DocumentMetadataPost,
#     document_record_storage: FromDishka[DocumentRecordStorageService],
#     metadata_service: FromDishka[DocumentMetadataService],
#     permission_storage: FromDishka[DocumentPermissionStorageService],
#     request: Request,
#     logged_user: LoggedUser
# ) -> DocumentMetadataGet:
#     """
#     Endpoint to retrieve a specific document metadata by its PID.
#     """

#     return await update_metadata_prefix(
#         pid=pid, prefix=PID_PREFIX, document_metadata=document_metadata,
#         document_record_storage=document_record_storage,
#         metadata_service=metadata_service, logged_user=logged_user,
#         permission_storage=permission_storage, request=request
#     )
