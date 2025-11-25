import json
import logging
from uuid import uuid4
from datetime import datetime, timezone

from models import DocumentMetadata, DocumentMetadataHistory, DocumentMetadataHistoryEntry, PidRecord
from application.exceptions.types import NotFoundException
from services.document_storage.service import DocumentRecordStorageService
from services.metadata.service import DocumentMetadataService
from services.file_storage.service import FileStorageService

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
    document_record_storage: DocumentRecordStorageService,
    file_storage: FileStorageService,
    pid_record: PidRecord | None = None
) -> DocumentMetadata:
    metadata = await metadata_service.get_document_metadata(pid, pid_record=pid_record)
    original_metadata = metadata.to_dict()

    # Update the metadata with the provided fields
    for field, value in document_metadata.model_dump().items():
        if value is not None:
            setattr(metadata, field, value)

    if metadata.to_dict() == original_metadata:
        logger.debug(f"No changes detected in metadata for PID '{pid}'. Skipping update.")
        return metadata

    # Save the updated metadata
    metadata = await metadata_service.update_document_metadata(pid, metadata)

    # Set `updated_at` to current time for document record
    try:
        await document_record_storage.document_is_updated(pid, datetime.now(timezone.utc))
    except Exception as e:
        logger.warning(f"Failed to update document record `updated_at` for PID '{pid}': {e}")


    metadata_history_storage_id = DocumentMetadataHistory.get_metadata_history_storage_id(pid)
    history_data = b""
    try:
        iterator = file_storage.retrieve_file(metadata_history_storage_id, ignore_compression=True)
        history_data = b""
        async for chunk in iterator:
            history_data += chunk
        logger.debug(f"Retrieved existing metadata history for PID '{pid}', size {len(history_data)} bytes.")
    except NotFoundException:
        logger.debug(f"No existing metadata history found for PID '{pid}', creating new history document.")

    try:
        history_str = history_data.decode('utf-8') if history_data else "{}"
        history_dict = json.loads(history_str)
        history = DocumentMetadataHistory.from_dict(history_dict)
    except json.JSONDecodeError as e:
        logger.warning(f"Cannot updated metadata history, failed to decode existing metadata history for PID '{pid}': {e}")
        return metadata
    except Exception as e:
        logger.warning(f"Cannot updated metadata history, failed to retrieve existing metadata history for PID '{pid}': {e}")
        return metadata

    new_entry = DocumentMetadataHistoryEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        metadata=metadata
    )
    history.history[uuid4().hex] = new_entry

    # Delete previous history file
    try:
        await file_storage.delete_file(metadata_history_storage_id)
    except Exception as e:
        logger.warning(f"Failed to delete previous metadata history for PID '{pid}': {e}")
        return metadata

    # Store the updated history
    try:
        logger.debug(f"Storing updated metadata history for PID '{pid}': {history.to_dict()}.")
        history_bytes = json.dumps(history.to_dict()).encode('utf-8')
        logger.debug(f"Storing updated metadata history for PID '{pid}': {len(history_bytes)} bytes.")
        await file_storage.store_file(metadata_history_storage_id, history_bytes, ignore_compression=True)
        logger.debug(f"Metadata history for PID '{pid}' updated successfully.")
    except Exception as e:
        logger.warning(f"Failed to store updated metadata history for PID '{pid}': {e}")

    return metadata
