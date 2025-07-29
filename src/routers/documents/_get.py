import logging

from fastapi import status, APIRouter
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.documentation.openapi_generation import EXAMPLE_EMAIL, EXAMPLE_UUID, EXAMPLE_DOCUMENT_VERSION, EXAMPLE_DOCUMENT_STORAGE
from application.exceptions.responses import EXCEPTION_SCHEMA
from application.exceptions.types import NotFoundException, ServiceUnavailableException, UnauthorizedException, ForbiddenException
from services.document_storage.service import DocumentRecordStorageService
from services.user_storage.service import UserStorageService
from application.settings import PID_PREFIX

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="",
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
    parent_document_pid: str | None = Field(None, examples=[EXAMPLE_UUID], description="PID of the previous document version.")


documentation = {
    "summary": "Get Document Record info",
    "description": "This endpoint retrieves a specific document record info by its PID and prefix.",
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns the document record with its unique identifier (pid), version, storage URL, owner email, and optional parent document PID.",
    "responses": {
        status.HTTP_404_NOT_FOUND: EXCEPTION_SCHEMA[NotFoundException, "The specified document PID does not exist."],
        status.HTTP_503_SERVICE_UNAVAILABLE: EXCEPTION_SCHEMA[ServiceUnavailableException]
    }
}


@router.get("/{prefix}/{pid}", **documentation)
async def get_document_prefix(
    prefix: str,
    pid: str,
    document_record_storage: FromDishka[DocumentRecordStorageService],
    user_storage_service: FromDishka[UserStorageService]
) -> DocumentRecordGet:
    """
    Endpoint to retrieve a specific document record by its PID and prefix.
    """

    pid = f"{prefix}/{pid}"
    # Fetch the document record by PID
    record = await document_record_storage.get_document_by_pid(pid)

    # Get owner email by user ID
    try:
        owner = await user_storage_service.get_user_by_id(record.owner_id)
        owner_email = owner.email
    except NotFoundException as e:
        logger.warning(f"Owner with ID {record.owner_id} not found for document PID {pid}: {e}")
        owner_email = None

    return DocumentRecordGet(
        pid=record.pid,
        version=record.version,
        storage_url=record.storage_url,
        owner_email=owner_email or "Unknown",
        parent_document_pid=record.parent_doc_pid
    )
