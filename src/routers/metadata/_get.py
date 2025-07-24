import logging

from fastapi import status, APIRouter
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.documentation.openapi_generation import EXAMPLE_METADATA_TITLE, EXAMPLE_METADATA_DESCRIPTION, EXAMPLE_METADATA_KEYWORDS, EXAMPLE_METADATA_AUTHOR
from application.exceptions.responses import EXCEPTION_SCHEMA
from application.exceptions.types import NotFoundException, ServiceUnavailableException
from services.document_storage.service import DocumentRecordStorageService
from services.metadata.service import DocumentMetadataService
from models import DocumentMetadata

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="",
    route_class=DishkaRoute
)


class DocumentMetadataGet(BaseModel):
    """
    Response model for document metadata.
    """
    title: str | None = Field(default=None, examples=[EXAMPLE_METADATA_TITLE])
    description: str | None = Field(default=None, examples=[EXAMPLE_METADATA_DESCRIPTION])
    keywords: list[str] | None = Field(default=None, examples=[EXAMPLE_METADATA_KEYWORDS])
    author: str | None = Field(default=None, examples=[EXAMPLE_METADATA_AUTHOR])

    @classmethod
    def from_metadata(cls, metadata: DocumentMetadata) -> 'DocumentMetadataGet':
        """
        Convert DocumentMetadata to DocumentMetadataGet.
        
        :param metadata: DocumentMetadata instance.
        :return: DocumentMetadataGet instance.
        """
        return cls(**{field: getattr(metadata, field) for field in cls.model_fields.keys()})


documentation = {
    "summary": "Get Document Metadata",
    "description": "This endpoint retrieves metadata for a specific document by its PID and prefix.",
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns the document metadata including title, description, and keywords.",
    "responses": {
        status.HTTP_404_NOT_FOUND: EXCEPTION_SCHEMA[NotFoundException, "The specified document PID does not exist."],
        status.HTTP_503_SERVICE_UNAVAILABLE: EXCEPTION_SCHEMA[ServiceUnavailableException]
    }
}


@router.get("/{prefix}/{pid}/metadata", **documentation)
async def get_metadata_prefix(
    prefix: str,
    pid: str,
    document_record_storage: FromDishka[DocumentRecordStorageService],
    metadata_service: FromDishka[DocumentMetadataService],
) -> DocumentMetadataGet:
    """
    Endpoint to retrieve metadata for a specific document by its PID and prefix.
    """

    pid = f"{prefix}/{pid}"
    # Fetch the document record by PID to verify it is handled by this server instance
    await document_record_storage.get_document_by_pid(pid)

    metadata = await metadata_service.get_document_metadata(pid)
    return DocumentMetadataGet.from_metadata(metadata)


# documentation.update({
#     "description": "This endpoint retrieves a specific document metadata by its PID. "
#                    "Prefix is set by default to the application PID prefix.",
# })


# @router.get("/{pid}/metadata", **documentation)
# async def get_metadata(
#     pid: str,
#     document_record_storage: FromDishka[DocumentRecordStorageService],
#     metadata_service: FromDishka[DocumentMetadataService]
# ) -> DocumentMetadataGet:
#     """
#     Endpoint to retrieve a specific document metadata by its PID.
#     """

#     return await get_metadata_prefix(
#         pid=pid, prefix=PID_PREFIX, document_record_storage=document_record_storage, metadata_service=metadata_service
#     )
