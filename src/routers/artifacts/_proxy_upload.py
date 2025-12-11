import logging

from fastapi import APIRouter, status, Path, UploadFile, Query
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from models import PresignedURLOperationType, PresignedURL, PidRecord, PidType
from application.exceptions.types import BadRequestException, UnauthorizedException, NotFoundException, ServiceUnavailableException, ForbiddenException, InternalServerErrorException
from application.settings import APP_URL
from application.documentation.openapi_generation import EXAMPLE_UUID, EXAMPLE_HASH
from application.exceptions.responses import EXCEPTION_SCHEMA
from services.artifact_storage.service import ArtifactRecordStorageService
from services.file_storage.service import ArtifactFileStorageService, PresignedURLService
from services.pid.service import PidService

__all__ = ("router",)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="",
    route_class=DishkaRoute
)


class ArtifactUploadResponse(BaseModel):
    """
    Response model for artifact upload URL.
    """
    pid: str = Field(..., examples=[EXAMPLE_UUID])
    hash: str | None = Field(None, examples=[EXAMPLE_HASH], description="SHA-256 hash of the uploaded artifact content, if available.")


documentation = {
    "summary": "Proxy Artifact Upload",
    "description": "This endpoint proxies the upload of an artifact using a presigned URL token. After the upload, the token will be invalidated.",
    "status_code": status.HTTP_200_OK,
    "response_description": "Upload the artifact content, either streamed or as a full response.",
    "response_model": None,
    "responses": {
        status.HTTP_401_UNAUTHORIZED: EXCEPTION_SCHEMA[UnauthorizedException, "The token is invalid or has expired."],
        status.HTTP_403_FORBIDDEN: EXCEPTION_SCHEMA[ForbiddenException, "You do not have permission to access this artifact."],
        status.HTTP_404_NOT_FOUND: EXCEPTION_SCHEMA[NotFoundException, "The specified artifact PID does not exist."],
        status.HTTP_503_SERVICE_UNAVAILABLE: EXCEPTION_SCHEMA[ServiceUnavailableException, "The storage service is currently unavailable." ]
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
                                "description": "The document file to be uploaded."
                            }
                        }
                    }
                }
            }
        },
    }
}


@router.put("/proxy/upload/{token}", **documentation)
async def proxy_artifact_upload(
    artifact_record_storage: FromDishka[ArtifactRecordStorageService],
    presigned_url_service: FromDishka[PresignedURLService],
    file_storage_service: FromDishka[ArtifactFileStorageService],
    pid_service: FromDishka[PidService],
    document_file: UploadFile,
    token: str = Path(..., description="Token for the presigned upload URL.", examples=["example-token-1234"]),
    pid: str = Query(..., description="PID of the artifact being uploaded.", examples=[EXAMPLE_UUID])
) -> ArtifactUploadResponse:
    """
    Endpoint to proxy the upload of an artifact using a presigned URL token.
    """
    presigned_url: PresignedURL = await presigned_url_service.get_presigned_url_from_token(token=token, raise_not_found=False)
    if not presigned_url or presigned_url.is_expired() or presigned_url.operation_type != PresignedURLOperationType.UPLOAD:
        raise UnauthorizedException("The token is invalid or has expired.")

    artifact_record = await artifact_record_storage.get_artifact_by_pid(pid=presigned_url.artifact_pid, raise_not_found=False)
    if not artifact_record:
        raise NotFoundException("The specified artifact PID does not exist.")
    
    if artifact_record.owner_id != presigned_url.user_id:
        raise ForbiddenException("You do not have permission to access this artifact.")

    if artifact_record.pid != pid:
        raise UnauthorizedException("The provided PID does not match the artifact associated with the token.")
    
    file_hash = None
    try:
        file_hash = await file_storage_service.store_file_from_uploadfile(artifact_record.storage_id, document_file, ignore_compression=True)
    except Exception as e:
        raise BadRequestException(f"Failed to read document file: {e}")
    
    updated_db = False
    try:

        artifact_record.hash = file_hash
        artifact_record.valid = True
        artifact_record = await artifact_record_storage.update_artifact(artifact_record)
        updated_db = True

        await presigned_url_service.delete_presigned_url(token=token)

        # create PID record now that upload is complete
        pid_record = PidRecord(
            pid=artifact_record.pid,
            type=PidType.ARTIFACT,
            url=f"{APP_URL.rstrip('/')}/artifacts/{artifact_record.pid}/download/url",
            hash=file_hash,
            hash_algorithm="sha256"
        )

        pid_record = await pid_service.save_pid_record(pid_record)
    
        return ArtifactUploadResponse(
            pid=artifact_record.pid,
            hash=file_hash
        )
    except Exception as e:
        logger.error(f"Error while proxying artifact upload for PID '{artifact_record.pid}': {e}")
        logger.info("Deleting stored file due to error during artifact creation.")

        # If any error occurs, clean up the stored file
        try:
            await file_storage_service.delete_file(artifact_record.storage_id)
        except Exception as e:
            logger.warning(f"Failed to delete stored file after artifact creation error: {e}")

        if updated_db:
            # If the artifact record was updated in the DB but PID creation failed, set valid=False
            logger.info("Setting artifact record valid=False due to PID creation failure.")
            try:
                artifact_record.valid = False
                await artifact_record_storage.update_artifact(artifact_record)
            except Exception as db_e:
                logger.warning(f"Failed to set artifact record valid=False after PID creation failure: {db_e}")

        raise InternalServerErrorException("The artifact upload failed.") from e
