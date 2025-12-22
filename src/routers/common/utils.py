import logging
from typing import AsyncGenerator

from fastapi.responses import StreamingResponse

from models import DocumentRecord
from application.exceptions.types import NotFoundException, ServiceUnavailableException
from services.file_storage.service import FileStorageService, DocumentNotCompressedException

logger = logging.getLogger(__name__)


async def get_file_stream(
    pid: str,
    document_record: DocumentRecord,
    file_storage_service: FileStorageService,
    skip_decompression: bool
) -> AsyncGenerator:
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

        # if accept_encoding and accept_encoding != file_storage_service.get_compression_standard().value:
        #     raise BadRequestException(f"Unsupported Accept-Encoding '{accept_encoding}'. Supported: '{file_storage_service.get_compression_standard().value}'")

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

        return delegating_gen()
    except NotFoundException:
        raise NotFoundException(f"Document with PID '{pid}' not found.")
    except ServiceUnavailableException as e:
        raise ServiceUnavailableException(f"Failed to retrieve document with PID '{pid}'") from e


async def get_file_str(
    pid: str,
    document_record: DocumentRecord,
    file_storage_service: FileStorageService,
    skip_decompression: bool = False
) -> str:
    """
    Utility function to get the full content of a document file as a string.
    Mainly for testing or small files, as it reads the entire content into memory.
    """
    content_bytes = b""
    delegating_gen = await get_file_stream(
        pid,
        document_record,
        file_storage_service,
        skip_decompression=skip_decompression
    )
    async for chunk in delegating_gen:
        content_bytes += chunk
    return content_bytes.decode('utf-8')


async def get_file_bytes(
    pid: str,
    document_record: DocumentRecord,
    file_storage_service: FileStorageService,
    skip_decompression: bool = False
) -> bytes:
    """
    Utility function to get the full content of a document file as bytes.
    Mainly for testing or small files, as it reads the entire content into memory.
    """
    content_bytes = b""
    delegating_gen = await get_file_stream(
        pid,
        document_record,
        file_storage_service,
        skip_decompression=skip_decompression
    )
    async for chunk in delegating_gen:
        content_bytes += chunk
    return content_bytes
