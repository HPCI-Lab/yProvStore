import logging

from fastapi import status, APIRouter
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.documentation.openapi_generation import EXAMPLE_METADATA_TITLE, EXAMPLE_METADATA_DESCRIPTION, EXAMPLE_METADATA_KEYWORDS, EXAMPLE_METADATA_AUTHOR
from application.exceptions.responses import EXCEPTION_SCHEMA
from application.exceptions.types import NotFoundException, ServiceUnavailableException
from services.document_storage.service import DocumentRecordStorageService
from services.metadata.service import DocumentMetadataService
from services.pid.service import PidService
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
    "description": "This endpoint retrieves metadata for a specific document by its PID.",
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns the document metadata including title, description, and keywords.",
    "responses": {
        status.HTTP_404_NOT_FOUND: EXCEPTION_SCHEMA[NotFoundException, "The specified document PID does not exist."],
        status.HTTP_503_SERVICE_UNAVAILABLE: EXCEPTION_SCHEMA[ServiceUnavailableException]
    }
}


@router.get("/{pid:path}/metadata", **documentation)
async def get_metadata(
    pid: str,
    document_record_storage: FromDishka[DocumentRecordStorageService],
    pid_service: FromDishka[PidService],
    metadata_service: FromDishka[DocumentMetadataService],
) -> DocumentMetadataGet:
    """
    Endpoint to retrieve metadata for a specific document by its PID.
    """

    # Fetch the document record by PID to verify it is handled by this server instance
    document_record = await document_record_storage.get_document_by_pid(pid)

    pid_record = await pid_service.get_pid_record(pid)

    if pid_record.lineage_id != document_record.lineage_id:
        logger.warning(f"PID record lineage_id '{pid_record.lineage_id}' does not match document record lineage_id '{document_record.lineage_id}' for PID '{pid}'. Updating document record.")
        document_record.lineage_id = pid_record.lineage_id
        await document_record_storage.update_document(document_record)

    metadata = await metadata_service.get_document_metadata(pid, pid_record)
    return DocumentMetadataGet.from_metadata(metadata)
