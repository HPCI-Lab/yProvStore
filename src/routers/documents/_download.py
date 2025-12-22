import logging
from typing import Optional

from fastapi import APIRouter, status, Header
from fastapi.responses import StreamingResponse, Response
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.settings import DOCUMENT_DOWNLOAD_SIZE_LIMIT_MB
from application.exceptions.types import UnauthorizedException, NotFoundException, ServiceUnavailableException, PayloadTooLargeException
from application.exceptions.responses import EXCEPTION_SCHEMA
from services.file_storage.service import FileStorageService
from services.document_storage.service import DocumentRecordStorageService
from routers.common.utils import get_file_stream, get_file_str
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

    skip_decompression = accept_encoding == file_storage_service.get_compression_standard().value

    encoding_headers = {}
    if skip_decompression:
        encoding_headers["Content-Encoding"] = file_storage_service.get_compression_standard().value
    
    if not stream:
        # read all content into memory (not ideal for large files)

        # If bigger than limit, raise error
        file_size = await file_storage_service.get_file_size(document_record.storage_id)
        if file_size > DOCUMENT_DOWNLOAD_SIZE_LIMIT_MB * 1024 * 1024:
            raise PayloadTooLargeException(
                f"Requested document is too large to be downloaded without streaming ({DOCUMENT_DOWNLOAD_SIZE_LIMIT_MB} MB limit)."
                " Please use stream=true to download document in stream mode."
            )

        content_str = await get_file_str(
            pid,
            document_record,
            file_storage_service,
            skip_decompression=skip_decompression
        )
        return Response(
            content=content_str,
            media_type="application/json",
            headers=encoding_headers
        )

    delegating_gen = await get_file_stream(
        pid,
        document_record,
        file_storage_service,
        skip_decompression=skip_decompression
    )

    return StreamingResponse(
        delegating_gen,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={pid}.json",
            **encoding_headers
        }
    )
