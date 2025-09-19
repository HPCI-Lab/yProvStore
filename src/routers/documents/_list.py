import logging
from datetime import datetime

from fastapi import APIRouter, status, Query
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.documentation.openapi_generation import EXAMPLE_EMAIL, EXAMPLE_UUID, EXAMPLE_DOCUMENT_VERSION, EXAMPLE_DOCUMENT_STORAGE
from services.document_storage.service import DocumentRecordStorageService
from services.user_storage.service import UserStorageService

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
    owner_email: str | None = Field(..., examples=[EXAMPLE_EMAIL])
    parent_document_pid: str | None = Field(None, examples=[EXAMPLE_UUID], description="PID of the previous document version.")


documentation = {
    "summary": "List Document Records",
    "description": ("This endpoint retrieves a list of paginated document records available in this server instance."
                    " Default page size is 10, and pagination starts from page 0."),
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns a list of document records, each containing a unique identifier (pid), version, storage URL, owner email, and optional parent document PID."
}


@router.get("", **documentation)
async def list_documents(
    document_record_storage: FromDishka[DocumentRecordStorageService],
    user_storage_service: FromDishka[UserStorageService],
    page: int = 0,
    page_size: int = 10,
    updated_after: datetime | None = Query(
        None,
        description="Return documents updated after this timestamp (ISO 8601 format).",
        examples=["2024-06-01T00:00:00Z", "2024-06-01"]
    ),
) -> list[DocumentRecordGet]:
    """
    Endpoint to list all document records available in the storage.
    This endpoint retrieves all document records and returns them in a standardized format.
    """

    # TODO: manage filtering

    records = await document_record_storage.list_documents(
        page=page,
        page_size=page_size,
        updated_after=updated_after
    )

    user_emails: dict[str, str] = await user_storage_service.get_user_emails(
        ids=[record.owner_id for record in records]
    )

    return [
        DocumentRecordGet(
            pid=record.pid,
            version=record.version,
            storage_url=record.storage_url,
            owner_email=user_emails.get(record.owner_id, "Unknown"),
            parent_document_pid=record.parent_doc_pid
        )
        for record in records
    ]
