import logging

from fastapi import APIRouter, status, Query
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from models.artifact import PresignedURLOperationType, PresignedURL
from application.settings import PROXY_ARTIFACT_STORAGE, APP_URL, MINIO_ARTIFACT_BUCKET
from application.documentation.openapi_generation import EXAMPLE_UUID, EXAMPLE_ARTIFACT_STORAGE, EXAMPLE_HASH, EXAMPLE_ARTIFACT_FILENAME
from services.artifact_storage.service import ArtifactRecordStorageService
from services.file_storage.service import FileStorageService, PresignedURLService

__all__ = ("router",)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="",
    route_class=DishkaRoute
)


class ArtifactDownloadURL(BaseModel):
    """
    Response model for artifact download URL.
    """
    download_url: str = Field(..., examples=[EXAMPLE_ARTIFACT_STORAGE], description="URL of the endpoint to request the artifact download (presigned URL)")
    filename: str = Field(..., examples=[EXAMPLE_ARTIFACT_FILENAME], description="Filename of the artifact.")
    hash: str | None = Field(None, examples=[EXAMPLE_HASH], description="SHA-256 hash of the artifact content, if available.")


documentation = {
    "summary": "Get Artifact Download URL",
    "description": "This endpoint retrieves a presigned download URL for an artifact by its PID.",
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns a presigned URL for downloading the specified artifact."
}


@router.get("/{pid:path}/download/url", **documentation)
async def get_artifact_download_url(
    artifact_record_storage: FromDishka[ArtifactRecordStorageService],
    presigned_url_service: FromDishka[PresignedURLService],
    file_storage_service: FromDishka[FileStorageService],
    pid: str = Query(
        ...,
        description="The PID of the artifact to retrieve the download URL for.",
        examples=[EXAMPLE_UUID]
    )
) -> ArtifactDownloadURL:
    """
    Endpoint to generate and retrieve presigned download URL for an artifact by its PID.
    """

    artifact_record = await artifact_record_storage.get_artifact_by_pid(pid=pid)

    if not PROXY_ARTIFACT_STORAGE:
        presigned_url = await file_storage_service.get_download_presigned_url(storage_id=artifact_record.storage_id, bucket=MINIO_ARTIFACT_BUCKET)
    else:
        presigned_url: PresignedURL = await presigned_url_service.generate_presigned_url(
            user_id=artifact_record.owner_id,
            storage_id=artifact_record.storage_id,
            operation_type=PresignedURLOperationType.DOWNLOAD,
            filename=artifact_record.filename
        )
        presigned_url = f"{APP_URL.rstrip('/')}/artifacts/proxy/download/{presigned_url.token}"

    return ArtifactDownloadURL(
        download_url=presigned_url,
        filename=artifact_record.filename,
        hash=artifact_record.hash
    )
