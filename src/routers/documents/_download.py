import logging
from typing import Optional

from fastapi import APIRouter, status, Header
from fastapi.responses import StreamingResponse, Response
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.exceptions.types import UnauthorizedException, NotFoundException, ServiceUnavailableException, BadRequestException
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
    "description": ("This endpoint allows the user to download a document by its PID. <br><br>"
                    "The document is retrieved from the storage system using the provided PID and prefix. <br><br>"
                    "By default, the document is returned as a streaming response. "
                    "Use the `stream` query parameter set to `false` to return the entire JSON content in the response body instead. <br><br>"
                    "You can pass valid `Accept-Encoding` headers to directly download compressed content instead of decompressing it server-side. "
                    "At the moment the only supported compression is `zstd`."),
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns the requested document file as a streaming response (default) or complete JSON content.",
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
        status.HTTP_401_UNAUTHORIZED: EXCEPTION_SCHEMA[UnauthorizedException],
        status.HTTP_404_NOT_FOUND: EXCEPTION_SCHEMA[NotFoundException, "The specified document PID does not exist."],
        status.HTTP_503_SERVICE_UNAVAILABLE: EXCEPTION_SCHEMA[ServiceUnavailableException]
    },
}


@router.get("/{pid:path}", **documentation)
async def download_document_prefix(
    pid: str,
    file_storage_service: FromDishka[FileStorageService],
    document_storage_service: FromDishka[DocumentRecordStorageService],
    stream: bool = True,
    accept_encoding: Optional[str] = Header(None),  # client can send Accept-Encoding header
) -> StreamingResponse | Response:
    """
    Download a document file by its PID and prefix.

    :param pid: The unique identifier of the document to be downloaded.
    :param file_storage_service: The service to handle file storage operations.
    :param document_storage_service: The service to handle document record operations.
    :param stream: Whether to return a streaming response (True, default) or complete content (False).
    :param accept_encoding: Optional Accept-Encoding header from the client.
    :return: The requested document file as a streaming response or complete JSON content.
    """

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

        if accept_encoding and accept_encoding != file_storage_service.get_compression_standard().value:
            return BadRequestException(f"Unsupported Accept-Encoding '{accept_encoding}'. Supported: '{file_storage_service.get_compression_standard().value}'")
        
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
            async for chunk in stream_gen:
                yield chunk
                yielded += len(chunk)

        encoding_headers = {}
        if skip_decompression:
            encoding_headers["Content-Encoding"] = file_storage_service.get_compression_standard().value
        
        if not stream:
            # read all content into memory (not ideal for large files)
            content_bytes = b""
            async for chunk in delegating_gen():
                content_bytes += chunk
            content_str = content_bytes.decode('utf-8')
            return Response(
                content=content_str,
                media_type="application/json",
                headers=encoding_headers
            )
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
