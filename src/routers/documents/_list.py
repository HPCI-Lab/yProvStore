import logging

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.documentation.openapi_generation import EXAMPLE_EMAIL, EXAMPLE_UUID, EXAMPLE_DOCUMENT_VERSION, EXAMPLE_DOCUMENT_STORAGE
from services.document_storage.service import DocumentRecordStorageService
from services.user_storage.service import UserStorageService
from application.exceptions.types import NotFoundException

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
    pid: str = Field(..., example=EXAMPLE_UUID)
    version: int = Field(..., example=EXAMPLE_DOCUMENT_VERSION)
    storage_url: str = Field(..., example=EXAMPLE_DOCUMENT_STORAGE)
    owner_email: str | None = Field(..., example=EXAMPLE_EMAIL)
    parent_document_pid: str | None = Field(None, example=EXAMPLE_UUID, description="PID of the previous document version.")


documentation = {
    "summary": "List Document Records",
    "description": "This endpoint retrieves a list of all document records available in this server instance.",
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns a list of document records, each containing a unique identifier (pid), version, storage URL, owner email, and optional parent document PID."
}


@router.get("", **documentation)
async def list_documents(
    document_record_storage: FromDishka[DocumentRecordStorageService],
    user_storage_service: FromDishka[UserStorageService]
) -> list[DocumentRecordGet]:
    """
    Endpoint to list all document records available in the storage.
    This endpoint retrieves all document records and returns them in a standardized format.
    """

    # TODO: manage pagination and filtering

    records = await document_record_storage.list_documents()

    out_records = []
    for record in records:
        # Get owner email by user ID
        try:
            owner = await user_storage_service.get_user_by_id(record.owner_id)
            owner_email = owner.email
        except NotFoundException:
            owner_email = None
            logger.warning(f"Owner with ID {record.owner_id} not found for document {record.pid}.")
        out_records.append(
            DocumentRecordGet(
                pid=record.pid,
                version=record.version,
                storage_url=record.storage_url,
                owner_email=owner_email,
                parent_document_pid=record.parent_doc_pid
            )
        )
    return out_records
