import logging

from fastapi import APIRouter, status, Query, Path
from fastapi.responses import StreamingResponse, Response
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from models import PresignedURLOperationType, PresignedURL
from application.exceptions.types import UnauthorizedException, NotFoundException, ServiceUnavailableException, ForbiddenException, InternalServerErrorException
from application.exceptions.responses import EXCEPTION_SCHEMA
from application.documentation.openapi_generation import EXAMPLE_UUID
from services.artifact_storage.service import ArtifactRecordStorageService
from services.file_storage.service import ArtifactFileStorageService, PresignedURLService

__all__ = ("router",)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="",
    route_class=DishkaRoute
)


documentation = {
    "summary": "Proxy Artifact Download",
    "description": "This endpoint proxies the download of an artifact using a presigned URL token. After the download, the token will be invalidated.",
    "status_code": status.HTTP_200_OK,
    "response_description": "Download the artifact content, either streamed or as a full response.",
    "response_model": None,
    "responses": {
        status.HTTP_200_OK: {
            "description": "The requested document file has been successfully retrieved.",
            "content": {
                "application/octet-stream": {
                    "schema": {
                        "type": "string",
                        "format": "binary"
                    }
                },
                "application/json": {
                    "schema": {
                        "type": "object",
                        "description": "Complete JSON document content (when stream=false)"
                    }
                }
            }
        },
        status.HTTP_401_UNAUTHORIZED: EXCEPTION_SCHEMA[UnauthorizedException, "The token is invalid or has expired."],
        status.HTTP_403_FORBIDDEN: EXCEPTION_SCHEMA[ForbiddenException, "You do not have permission to access this artifact."],
        status.HTTP_404_NOT_FOUND: EXCEPTION_SCHEMA[NotFoundException, "The specified artifact PID does not exist."],
        status.HTTP_503_SERVICE_UNAVAILABLE: EXCEPTION_SCHEMA[ServiceUnavailableException, "The storage service is currently unavailable." ]
    },
}


@router.get("/proxy/download/{token}", **documentation)
async def proxy_artifact_download(
    artifact_record_storage: FromDishka[ArtifactRecordStorageService],
    presigned_url_service: FromDishka[PresignedURLService],
    file_storage_service: FromDishka[ArtifactFileStorageService],
    stream: bool = Query(True, description="Whether to stream the download or return the entire content.", examples=[True, False]),
    pid: str = Query(..., description="When provided, validate that the artifact PID matches the one associated with the token.", examples=[EXAMPLE_UUID]),
    token: str = Path(..., description="Token for the presigned upload URL.", examples=["example-token-1234"])
) -> StreamingResponse | Response:
    """
    Endpoint to proxy the download of an artifact using a presigned URL token.
    """
    presigned_url: PresignedURL = await presigned_url_service.get_presigned_url_from_token(token=token, raise_not_found=False)
    if not presigned_url or presigned_url.is_expired() or presigned_url.operation_type != PresignedURLOperationType.DOWNLOAD:
        raise UnauthorizedException("The token is invalid or has expired.")

    artifact_record = await artifact_record_storage.get_artifact_by_pid(pid=presigned_url.artifact_pid, raise_not_found=False)
    if not artifact_record:
        raise NotFoundException("The specified artifact PID does not exist.")
    
    if artifact_record.owner_id != presigned_url.user_id:
        raise ForbiddenException("You do not have permission to access this artifact.")

    if artifact_record.pid != pid:
        raise UnauthorizedException("The provided PID does not match the artifact associated with the token.")

    try:
        async def _read_first_chunk():
            # obtain async generator (do NOT await it)
            stream_gen = file_storage_service.retrieve_file(
                storage_id=artifact_record.storage_id,
                ignore_compression=True
            )
            # try to get first chunk to surface storage errors (NotFound/ServiceUnavailable/DocumentNotCompressedException) early
            try:
                first_chunk = await stream_gen.__anext__()
            except StopAsyncIteration:
                # empty file -> return an empty async generator
                async def empty_gen():
                    if False:
                        yield b""
                    return
                return StreamingResponse(
                    empty_gen(),
                    media_type="application/octet-stream",
                    headers={
                        "Content-Disposition": f"attachment; filename={artifact_record.filename}"
                    }
                )
            except NotFoundException:
                raise NotFoundException(f"The specified artifact PID does not exist.")
            except Exception as e:
                # any other exception from the storage read should be surfaced as service unavailable
                raise ServiceUnavailableException(f"Failed to retrieve document with PID '{artifact_record.pid}'") from e

            return first_chunk, stream_gen
        
        first_chunk, stream_gen = await _read_first_chunk()

        # delegating generator: yield the first chunk already read, then the rest
        async def delegating_gen():
            yield first_chunk
            yielded = len(first_chunk)
            async for chunk in stream_gen:
                yield chunk
                yielded += len(chunk)

        await presigned_url_service.delete_presigned_url(token=token)

        if not stream:
            # read all content into memory (not ideal for large files)
            content_bytes = b""
            async for chunk in delegating_gen():
                content_bytes += chunk
            content_str = content_bytes.decode('utf-8')
            return Response(content=content_str, media_type="application/json")
        return StreamingResponse(
            delegating_gen(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={artifact_record.filename}"}
        )
    except Exception as e:
        logger.error(f"Error while proxying artifact download for PID '{artifact_record.pid}': {e}")
        raise InternalServerErrorException("The artifact download failed.") from e
