from io import BytesIO

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse, Response
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.exceptions.types import UnauthorizedException, NotFoundException, ServiceUnavailableException
from application.exceptions.responses import EXCEPTION_SCHEMA
from services.file_storage.service import FileStorageService
from services.document_storage.service import DocumentRecordStorageService
# from services.permission_storage.service import DocumentPermissionStorageService


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
        # obtain async generator (do NOT await it)
        stream_gen = file_storage_service.retrieve_file(document_record.storage_id)

        # try to get first chunk to surface storage errors (NotFound/ServiceUnavailable) early
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
        except Exception as e:
            # any other exception from the storage read should be surfaced as service unavailable
            raise ServiceUnavailableException(f"Failed to retrieve document with PID '{pid}'") from e

        # delegating generator: yield the first chunk already read, then the rest
        async def delegating_gen():
            yield first_chunk
            async for chunk in stream_gen:
                yield chunk

        return StreamingResponse(
            delegating_gen(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={pid}.json"
            }
        )
    except NotFoundException:
        raise NotFoundException(f"Document with PID '{pid}' not found.")
    except ServiceUnavailableException as e:
        raise ServiceUnavailableException(f"Failed to retrieve document with PID '{pid}'") from e
