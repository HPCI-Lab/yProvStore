import logging

from fastapi import APIRouter, status, Query
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from models import PresignedURLOperationType, PresignedURL, ArtifactRecord, PidRecord, PidType
from application.exceptions.types import InternalServerErrorException
from application.settings import PROXY_ARTIFACT_STORAGE, APP_URL, MINIO_ARTIFACT_BUCKET
from application.documentation.openapi_generation import EXAMPLE_UUID, EXAMPLE_ARTIFACT_STORAGE, EXAMPLE_ARTIFACT_FILENAME
from services.artifact_storage.service import ArtifactRecordStorageService
from services.file_storage.service import FileStorageService, PresignedURLService
from services.pid.service import PidService
from routers.common.dependencies import LoggedUser

__all__ = ("router",)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="",
    route_class=DishkaRoute
)


class ArtifactUploadURLResponse(BaseModel):
    """
    Response model for artifact upload URL.
    """
    pid: str = Field(..., examples=[EXAMPLE_UUID])
    upload_url: str = Field(..., examples=[EXAMPLE_ARTIFACT_STORAGE], description="URL of the endpoint to request the artifact upload (presigned URL)")


documentation = {
    "summary": "Get Artifact Upload URL",
    "description": "This endpoint retrieves a presigned upload URL for an artifact.",
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns a presigned URL for uploading the specified artifact."
}


@router.get("/upload/url", **documentation)
async def get_artifact_upload_url(
    artifact_record_storage: FromDishka[ArtifactRecordStorageService],
    presigned_url_service: FromDishka[PresignedURLService],
    pid_service: FromDishka[PidService],
    file_storage_service: FromDishka[FileStorageService],
    logged_user: LoggedUser,
    filename: str = Query(
        ...,
        description="Filename of the artifact to be uploaded.",
        examples=[EXAMPLE_ARTIFACT_FILENAME]
    )
) -> ArtifactUploadURLResponse:
    """
    Endpoint to generate and retrieve presigned upload URL for an artifact.
    """

    new_pid = await pid_service.new_pid()
    if not new_pid:
        raise Exception("Failed to generate a new PID.")
    
    try:
        artifact_record = ArtifactRecord(
            pid=new_pid,
            storage_id=new_pid,
            owner_id=logged_user.id,
            filename=filename,
            hash=None,
            valid=not PROXY_ARTIFACT_STORAGE  # Mark as valid only if not proxying. If proxying, wait for upload completion.
        )
        await artifact_record_storage.save_artifact(artifact_record)

        if not PROXY_ARTIFACT_STORAGE:
            logger.warning("Warning: Artifact record created with valid=True but direct storage access is enabled. Cannot verify upload completion.")
            presigned_url = await file_storage_service.get_upload_presigned_url(storage_id=artifact_record.storage_id, bucket=MINIO_ARTIFACT_BUCKET)
            
            logger.warning("Warning: Saving PID record for artifact now but we are not sure whether the upload will complete successfully.")
            pid_record = PidRecord(
                pid=artifact_record.pid,
                type=PidType.ARTIFACT,
                url=f"{APP_URL.rstrip('/')}/artifacts/{artifact_record.pid}/download/url",
            )
            await pid_service.save_pid_record(pid_record)
        else:
            presigned_url: PresignedURL = await presigned_url_service.generate_presigned_url(
                user_id=artifact_record.owner_id,
                storage_id=artifact_record.storage_id,
                operation_type=PresignedURLOperationType.UPLOAD,
                filename=artifact_record.filename
            )
            presigned_url = f"{APP_URL.rstrip('/')}/artifacts/proxy/upload/{presigned_url.token}"
    except Exception as e:
        logger.error(f"Error while creating artifact upload URL: {e}")
        raise InternalServerErrorException("Failed to create artifact upload URL.") from e

    return ArtifactUploadURLResponse(
        pid=artifact_record.pid,
        upload_url=presigned_url
    )
