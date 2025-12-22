import logging
from datetime import datetime

from fastapi import APIRouter, status, Query
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.settings import APP_URL
from application.documentation.openapi_generation import EXAMPLE_EMAIL, EXAMPLE_UUID, EXAMPLE_ARTIFACT_STORAGE, EXAMPLE_HASH
from services.artifact_storage.service import ArtifactRecordStorageService
from services.user_storage.service import UserStorageService

__all__ = ("router",)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/artifacts",
    route_class=DishkaRoute
)


class ArtifactRecordGet(BaseModel):
    """
    Response model for listing available artifacts.
    """
    pid: str = Field(..., examples=[EXAMPLE_UUID])
    filename: str = Field(..., examples=[EXAMPLE_ARTIFACT_STORAGE], description="Filename of the artifact.")
    storage_url: str = Field(..., examples=[EXAMPLE_ARTIFACT_STORAGE], description="URL of the endpoint to request the artifact download (presigned URL)")
    owner_email: str | None = Field(..., examples=[EXAMPLE_EMAIL], description="Email of the artifact owner.")
    hash: str | None = Field(None, examples=[EXAMPLE_HASH], description="SHA-256 hash of the artifact content, if available.")


documentation = {
    "summary": "List Artifact Records",
    "description": ("This endpoint retrieves a list of paginated artifact records available in this server instance."
                    "Only valid artifacts are returned by default. Default page size is 10, and pagination starts from page 0.\n\n"
                    "The artifact URLs returned can be used to retrieve the presigned download URLs to download the artifact (two-step retrieval)."),
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns a list of artifact records, each containing a unique identifier (pid), storage URL and owner email." + \
                            " The hash field contains the SHA-256 hash of the artifact content, if available."
}


@router.get("", **documentation)
async def list_artifacts(
    artifact_record_storage: FromDishka[ArtifactRecordStorageService],
    user_storage_service: FromDishka[UserStorageService],
    page: int = 0,
    page_size: int = 10,
    updated_after: datetime | None = Query(
        None,
        description="Return artifacts updated after this timestamp (ISO 8601 format).",
        examples=["2024-06-01T00:00:00Z", "2024-06-01"]
    ),
    created_after: datetime | None = Query(
        None,
        description="Return artifacts created after this timestamp (ISO 8601 format).",
        examples=["2024-06-01T00:00:00Z", "2024-06-01"]
    ),
    pid: str | None = Query(
        None,
        description="When provided, return a list containing only the artifact with the given PID if found.",
        examples=[EXAMPLE_UUID]
    )
) -> list[ArtifactRecordGet]:
    """
    Endpoint to list all artifact records available in the storage.
    This endpoint retrieves all artifact records and returns them in a standardized format.
    """

    # TODO: manage filtering

    records = await artifact_record_storage.list_artifacts(
        page=page,
        page_size=page_size,
        updated_after=updated_after,
        created_after=created_after,
        pid=pid,
        valid=True
    )

    user_emails: dict[str, str] = await user_storage_service.get_user_emails(
        ids=[record.owner_id for record in records]
    )

    return [
        ArtifactRecordGet(
            pid=record.pid,
            filename=record.filename,
            storage_url=f"{APP_URL.rstrip('/')}/artifacts/{record.pid}/download/url",
            hash=record.hash,
            owner_email=user_emails.get(record.owner_id, "Unknown"),
        )
        for record in records
    ]
