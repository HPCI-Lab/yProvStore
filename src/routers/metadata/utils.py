import logging
from datetime import datetime, timezone

from models import DocumentMetadata
from services.document_storage.service import DocumentRecordStorageService
from services.metadata.service import DocumentMetadataService

from ._get import DocumentMetadataGet

logger = logging.getLogger(__name__)


class DocumentMetadataPost(DocumentMetadataGet):
    """
    Request model for updating document metadata.
    """
    pass


async def update_document_metadata(
    pid: str,
    document_metadata: DocumentMetadataPost,
    metadata_service: DocumentMetadataService,
    document_record_storage: DocumentRecordStorageService
) -> DocumentMetadata:
    metadata = await metadata_service.get_document_metadata(pid)

    # Update the metadata with the provided fields
    for field, value in document_metadata.model_dump().items():
        if value is not None:
            setattr(metadata, field, value)

    # Save the updated metadata
    metadata = await metadata_service.update_document_metadata(pid, metadata)

    # Set `updated_at` to current time for document record
    try:
        await document_record_storage.document_is_updated(pid, datetime.now(timezone.utc))
    except Exception as e:
        logger.warning(f"Failed to update document record `updated_at` for PID '{pid}': {e}")
    return metadata
