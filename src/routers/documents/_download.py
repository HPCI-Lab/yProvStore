import logging
from typing import Optional

from fastapi import APIRouter, status, Header
from fastapi.responses import StreamingResponse, Response
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.exceptions.types import UnauthorizedException, NotFoundException, ServiceUnavailableException
from application.exceptions.responses import EXCEPTION_SCHEMA
from services.file_storage.service import FileStorageService, DocumentNotCompressedException
from services.document_storage.service import DocumentRecordStorageService
# from services.permission_storage.service import DocumentPermissionStorageService

logger = logging.getLogger(__name__)


__all__ = ("router",)


router = APIRouter(
    prefix="",
    route_class=DishkaRoute
)


documentation = {
    "summary": "Download a Document file by its PID",
    "description": ("This endpoint allows the user to download a document by its PID. "
                    "The document is retrieved from the storage system using the provided PID and prefix."),
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns the requested document file.",
    "response_class": Response,
    "responses": {
        status.HTTP_200_OK: {
            "description": "The requested document file has been successfully retrieved.",
            "content": {
                "application/octet-stream": {}
            }
        },
        status.HTTP_401_UNAUTHORIZED: EXCEPTION_SCHEMA[UnauthorizedException],
        status.HTTP_404_NOT_FOUND: EXCEPTION_SCHEMA[NotFoundException, "The specified document PID does not exist."],
        status.HTTP_503_SERVICE_UNAVAILABLE: EXCEPTION_SCHEMA[ServiceUnavailableException]
    },
}


@router.get("/{prefix}/{pid}/download", **documentation)
async def download_document_prefix(
    pid: str,
    prefix: str,
    file_storage_service: FromDishka[FileStorageService],
    document_storage_service: FromDishka[DocumentRecordStorageService],
    accept_encoding: Optional[str] = Header(None),  # client can send Accept-Encoding header
) -> StreamingResponse:
    """
    Download a document file by its PID and prefix.

    :param pid: The unique identifier of the document to be downloaded.
    :param prefix: The prefix to be used for the document PID.
    :param file_storage_service: The service to handle file storage operations.
    :return: The requested document file.
    """

    pid = f"{prefix}/{pid}"
    document_record = await document_storage_service.get_document_by_pid(pid)

    try:

        async def _read_first_chunk(skip_decompression: bool):
            # obtain async generator (do NOT await it)
            stream_gen = file_storage_service.retrieve_file(document_record.storage_id, skip_decompression=skip_decompression)
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
                        "Content-Disposition": f"attachment; filename={pid}.json"
                    }
                )
            except NotFoundException:
                raise NotFoundException(f"Document with PID '{pid}' not found.")
            except ServiceUnavailableException as e:
                raise ServiceUnavailableException(f"Failed to retrieve document with PID '{pid}'") from e
            except DocumentNotCompressedException as e:
                raise e
            except Exception as e:
                # any other exception from the storage read should be surfaced as service unavailable
                raise ServiceUnavailableException(f"Failed to retrieve document with PID '{pid}'") from e
            
            return first_chunk, stream_gen
        
        skip_decompression = accept_encoding == file_storage_service.get_compression_standard().value
        if skip_decompression:
            logger.info(f"Client requested to skip decompression for document {pid} and directly return {file_storage_service.get_compression_standard().value}-compressed.")
        try:
            first_chunk, stream_gen = await _read_first_chunk(skip_decompression=skip_decompression)
        except DocumentNotCompressedException as e:
            # Should only happen if the client requested skip_decompression but the document is not compressed
            skip_decompression = False
            logger.warning(f"Client requested skip_decompression but document {pid} is not compressed.")
            first_chunk, stream_gen = await _read_first_chunk(skip_decompression=False)

        # delegating generator: yield the first chunk already read, then the rest
        async def delegating_gen():
            yield first_chunk
            yielded = len(first_chunk)
            logger.debug(yielded)
            async for chunk in stream_gen:
                yield chunk
                yielded += len(chunk)
                logger.debug(yielded)

        encoding_headers = {}
        if skip_decompression:
            encoding_headers["Content-Encoding"] = file_storage_service.get_compression_standard().value
        return StreamingResponse(
            delegating_gen(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={pid}.json",
                **encoding_headers
            }
        )
    except NotFoundException:
        raise NotFoundException(f"Document with PID '{pid}' not found.")
    except ServiceUnavailableException as e:
        raise ServiceUnavailableException(f"Failed to retrieve document with PID '{pid}'") from e
