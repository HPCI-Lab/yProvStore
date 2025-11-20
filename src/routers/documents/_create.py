import json
import logging
from typing import Optional

from fastapi import APIRouter, status, UploadFile, Form, Request, Header, Query
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.documentation.openapi_generation import EXAMPLE_DOCUMENT_DATA, EXAMPLE_EMAIL, EXAMPLE_UUID, EXAMPLE_DOCUMENT_VERSION, EXAMPLE_DOCUMENT_STORAGE, EXAMPLE_HASH
from models import DocumentRecord, PermissionLevel
from application.exceptions.responses import EXCEPTION_SCHEMA
from application.exceptions.types import UnauthorizedException, ForbiddenException, NotFoundException, ServiceUnavailableException, BadRequestException
from services.document_storage.service import DocumentRecordStorageService
from services.permission_storage.service import DocumentPermissionStorageService
from services.pid.service import PidService
from services.file_storage.service import FileStorageService
from services.metadata.service import DocumentMetadataService
from routers.metadata.utils import DocumentMetadataPost, update_document_metadata
from routers.common.dependencies import LoggedUser

__all__ = ("router",)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/documents",
    route_class=DishkaRoute
)


class DocumentRecordGet(BaseModel):
    """
    Response model for listing available documents.
    """
    pid: str = Field(..., examples=[EXAMPLE_UUID])
    version: int = Field(..., examples=[EXAMPLE_DOCUMENT_VERSION])
    storage_url: str = Field(..., examples=[EXAMPLE_DOCUMENT_STORAGE])
    owner_email: str = Field(..., examples=[EXAMPLE_EMAIL])
    hash: str | None = Field(None, examples=[EXAMPLE_HASH], description="SHA-256 hash of the document content, if available.")
    parent_document_pid: str | None = Field(None, examples=[EXAMPLE_UUID], description="PID of the previous document version.")
    lineage_id: str | None = Field(None, examples=[EXAMPLE_UUID], description="Lineage identifier, if available.")


class DocumentRecordCreate(DocumentMetadataPost):
    """
    Request model for the input data to publish a new document.
    """
    document_data: dict = Form(..., example=EXAMPLE_DOCUMENT_DATA, description="The document JSON data to be stored.")


documentation = {
    "summary": "Publish a Document Record",
    "description": (
        "This endpoint allows the user to publish a new document record with its associated data. "
        "The document is stored in the system, and a unique identifier (PID) is generated for it."
        "\n\nTo upload a document, exactly one of the following fields must be provided: "
        "`document_data` in the JSON request body, or `document_file` as a file upload.<br><br>"
        "Optional metadata may be provided through the `document_metadata` query parameter to set the initial metadata for the document. "
        "Each metadata field is optional; omit or set to an empty string/list to leave it unset. Fields available: `title`, `description`, `keywords` (array of strings), `author`."\
        "<br><br>You can fetch the metadata schema with the `/metadata/schema` endpoint and an example is available in the GET `/documents/{pid}/metadata` endpoint documentation."
    ),
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns the created document record",
    "responses": {
        status.HTTP_401_UNAUTHORIZED: EXCEPTION_SCHEMA[UnauthorizedException],
        status.HTTP_400_BAD_REQUEST: EXCEPTION_SCHEMA[BadRequestException, "Invalid document data provided as input."],
        status.HTTP_403_FORBIDDEN: EXCEPTION_SCHEMA[ForbiddenException, "You do not have permission to create a document under the specified parent document lineage."],
        status.HTTP_404_NOT_FOUND: EXCEPTION_SCHEMA[NotFoundException, "The specified parent document PID does not exist."],
        status.HTTP_503_SERVICE_UNAVAILABLE: EXCEPTION_SCHEMA[ServiceUnavailableException]
    },
    "openapi_extra": {
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "document_file": {
                                "type": "string",
                                "format": "binary",
                                "description": "The document file to be uploaded. Must be either JSON or plain text."
                            }
                        }
                    }
                },
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "document_data": {
                                "type": "object",
                                "example": EXAMPLE_DOCUMENT_DATA
                            }
                        }
                    }
                }
            }
        },
        "parameters": [
            {
                "name": "document_metadata",
                "in": "query",
                "required": False,
                "description": (
                    "Optional initial metadata for the document encoded as a JSON object. "
                    "Provide fields among: title (string), description (string), keywords (array of strings), author (string). "
                    "Omitted fields remain unset. Example: {\"title\":\"A Title\",\"keywords\":[\"k1\",\"k2\"],\"author\":\"Jane Doe\"}"
                ),
                "schema": {
                    "type": "string",
                    "example": '{"title": "A Title", "description": "Desc", "keywords": ["k1", "k2"], "author": "Jane Doe"}'
                }
            }
        ]
    }
}


@router.post("", **documentation)
async def create_document(
    request: Request,
    document_record_storage: FromDishka[DocumentRecordStorageService],
    file_storage_service: FromDishka[FileStorageService],
    permission_service: FromDishka[DocumentPermissionStorageService],
    pid_service: FromDishka[PidService],
    metadata_service: FromDishka[DocumentMetadataService],
    logged_user: LoggedUser,
    document_metadata: Optional[str] = None,
    parent_document_pid: str | None = None,
    document_file: UploadFile | None = None,
    content_encoding: Optional[str] = Header(None),  # client may send Content-Encoding header
) -> DocumentRecordGet:
    """
    Endpoint to publish a new document in the system.
    """

    data: DocumentRecordCreate | None = None
    if request.headers.get("Content-Type") == "application/json":
        try:
            json_data = await request.json()
        except Exception as e:
            raise BadRequestException(f"Invalid JSON data provided: {e}")
        data = DocumentRecordCreate.model_validate(json_data)

    # TODO: validate document?
    if document_file and data and data.document_data:
        raise BadRequestException(
            "Cannot provide both 'document_data' in request body and 'document_file' as uploaded file. Please provide only one of them."
        )
    if not document_file and not data:
        raise BadRequestException(
            "At least one of 'document_data' in request body or 'document_file' as uploaded file must be provided. Please provide one of them."
        )

    new_pid = await pid_service.new_pid()
    if not new_pid:
        raise Exception("Failed to generate a new PID.")
    
    if document_metadata:
        try:
            metadata_dict = json.loads(document_metadata)
            document_metadata = DocumentMetadataPost.model_validate(metadata_dict)
        except Exception as e:
            raise BadRequestException(f"Invalid document metadata provided: {e}")

    skip_compression = False
    if content_encoding:
        # Validate and set the content encoding
        if content_encoding != file_storage_service.get_compression_standard().value:
            raise BadRequestException(f"Unsupported Content-Encoding: {content_encoding}. Supported: {file_storage_service.get_compression_standard().value}")        
        skip_compression = True

    parent_document_record = None
    if parent_document_pid:
        # Validate if the parent document exists

        parent_document_record = await document_record_storage.get_document_by_pid(parent_document_pid)
        await permission_service.validate_user_permission(user=logged_user, doc=parent_document_record, permission_level=PermissionLevel.WRITE)

        # TODO: if allowed to push to a different yProv instance than parent document, then do this instead:
        # await pid_service.get_pid_record(parent_document_pid)

    new_document_record = DocumentRecord(
        pid=new_pid,
        version=0,  # Version will be set later after storing the file
        storage_id=new_pid,
        owner_id=logged_user.id,
        parent_doc_pid=parent_document_pid,
    )

    file_hash = None
    if data and data.document_data:
        document_data_bytes = json.dumps(data.document_data).encode('utf-8')
        file_hash = await file_storage_service.store_file(new_document_record.storage_id, document_data_bytes, skip_compression=skip_compression)
    else:
        try:
            if not document_file or not document_file.content_type or document_file.content_type not in ['application/json', 'text/plain']:
                raise BadRequestException(
                    "Unsupported file type: " + (document_file.content_type if document_file else "None") + ". Only JSON or plain text files are allowed."
                )
            file_hash = await file_storage_service.store_file_from_uploadfile(new_document_record.storage_id, document_file, skip_compression=skip_compression)
        except Exception as e:
            raise BadRequestException(f"Failed to read document file: {e}")

    stored_on_db = False
    previous_parent_lineage_id = parent_document_record.lineage_id if parent_document_record else None
    try:
        # Create the PID record (but do not save it yet)
        new_pid_record, finalize_fn = await pid_service.new_pid_record_from_document(
            new_pid, new_document_record.storage_url, parent_doc_pid=parent_document_pid, hash=file_hash
        )

        # Save the document record to db
        new_document_record.version = new_pid_record.version or 1
        new_document_record.hash = file_hash
        new_document_record.lineage_id = new_pid_record.lineage_id
        new_document_record = await document_record_storage.save_document(new_document_record)

        if parent_document_record and parent_document_record.lineage_id != new_document_record.lineage_id:
            logger.info(f"Updating parent document record lineage_id from '{parent_document_record.lineage_id}' to '{new_document_record.lineage_id}'")
            parent_document_record.lineage_id = new_document_record.lineage_id
            await document_record_storage.update_document(parent_document_record)
        stored_on_db = True

        # Finalize saving all involved PID records
        await finalize_fn()

        # Update the document metadata
        if document_metadata:
            logger.info(f"Updating document metadata for PID '{new_document_record.pid}'")
            try:
                await update_document_metadata(
                    new_document_record.pid,
                    document_metadata,
                    metadata_service,
                    document_record_storage
                )
            except Exception as e:
                logger.warning(f"Failed to update document metadata for PID '{new_document_record.pid}': {e}")
                pass
    except Exception as e:
        logger.error(f"Error occurred during document creation: {e}")
        logger.info("Deleting stored file due to error during document creation.")
        # If any error occurs, clean up the stored file
        try:
            await file_storage_service.delete_file(new_document_record.storage_id)
        except Exception as e:
            logger.warning(f"Failed to delete stored file after document creation error: {e}")

        if stored_on_db:
            # If the document was stored in the DB but PID creation failed, remove the document record
            logger.info("Deleting document record from DB due to error during PID creation.")
            try:
                await document_record_storage.delete_document(new_document_record.pid)
            except Exception as db_e:
                logger.warning(f"Failed to clean up document record after PID creation failure: {db_e}")

            if parent_document_record:
                # If the parent document's lineage_id was changed, revert it
                if parent_document_record.lineage_id != previous_parent_lineage_id:
                    logger.info(f"Reverting parent document record lineage_id back to '{previous_parent_lineage_id}'")
                    parent_document_record.lineage_id = previous_parent_lineage_id
                    try:
                        await document_record_storage.update_document(parent_document_record)
                    except Exception as revert_e:
                        logger.warning(f"Failed to revert parent document lineage_id after error: {revert_e}")
        raise e

    return DocumentRecordGet(
        pid=new_document_record.pid,
        version=new_document_record.version,
        storage_url=new_document_record.storage_url,
        owner_email=logged_user.email,
        hash=new_document_record.hash,
        parent_document_pid=new_document_record.parent_doc_pid,
        lineage_id=new_document_record.lineage_id
    )
 