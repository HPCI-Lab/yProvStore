import json

from fastapi import APIRouter, status, UploadFile, Form, Request
from pydantic import BaseModel
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.documentation.openapi_generation import EXAMPLE_DOCUMENT_DATA
from models import DocumentRecord, PermissionLevel
from application.exceptions.responses import EXCEPTION_SCHEMA
from application.exceptions.types import UnauthorizedException, ForbiddenException, NotFoundException, ServiceUnavailableException, BadRequestException
from services.document_storage.service import DocumentRecordStorageService
from services.permission_storage.service import DocumentPermissionStorageService
from services.pid.service import PidService
from services.file_storage.service import FileStorageService
from routers.documents._get import DocumentRecordGet
from routers.common.dependencies import LoggedUser

__all__ = ("router",)


router = APIRouter(
    prefix="/documents",
    route_class=DishkaRoute
)


class DocumentRecordCreate(BaseModel):
    """
    Request model for the input data to publish a new document.
    """
    document_data: dict = Form(..., example=EXAMPLE_DOCUMENT_DATA, description="The document JSON data to be stored.")


documentation = {
    "summary": "Publish a Document Record",
    "description": ("This endpoint allows the user to publish a new document record with its associated data. "
                    "The document is stored in the system, and a unique identifier (PID) is generated for it."
                    "\n\nTo upload a document, exactly one of the following fields must be provided: "
                    "`document_data` in the request body, or `document_file` as a file upload."),
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
                            },
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
                        },
                    }
                },
            }
        }
    }
}


@router.post("", **documentation)
async def create_document(
    request: Request,
    document_record_storage: FromDishka[DocumentRecordStorageService],
    file_storage_service: FromDishka[FileStorageService],
    permission_service: FromDishka[DocumentPermissionStorageService],
    pid_service: FromDishka[PidService],
    logged_user: LoggedUser,
    parent_document_pid: str | None = None,
    document_file: UploadFile | None = None,
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

    if data and data.document_data:
        document_data_bytes = json.dumps(data.document_data).encode('utf-8')
    else:
        try:
            if not document_file or not document_file.content_type or document_file.content_type not in ['application/json', 'text/plain']:
                raise BadRequestException(
                    f"Unsupported file type: {document_file.content_type if document_file else "None"}. Only JSON or plain text files are allowed."
                )
            document_data_bytes = await document_file.read()
        except Exception as e:
            raise BadRequestException(f"Failed to read document file: {e}")
    await file_storage_service.store_file(new_document_record.storage_id, document_data_bytes)

    new_pid_record = await pid_service.new_pid_record_from_document(new_pid, new_document_record.storage_url, parent_doc_pid=parent_document_pid)

    new_document_record.version = new_pid_record.version or 1
    new_document_record = await document_record_storage.save_document(new_document_record)

    return DocumentRecordGet(
        pid=new_document_record.pid,
        version=new_document_record.version,
        storage_url=new_document_record.storage_url,
        owner_email=logged_user.email,
        parent_document_pid=new_document_record.parent_doc_pid
    )
