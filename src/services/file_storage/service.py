import io
import os
import hashlib
import asyncio
import logging
import tempfile
import importlib

import aiofiles
from typing import AsyncIterator
import zstandard as zstd
from fastapi import UploadFile
from dishka import Provider, provide, Scope

from application import settings
from application.settings import TMP_PATH
from application.exceptions.types import ConflictException, NotFoundException, ServiceUnavailableException


logger = logging.getLogger(__name__)


ZSTD_LEVEL = 1  # low CPU, reasonable compression
READ_CHUNK = 1024 * 1024  # 1 MiB read chunks for streaming


class FileStorageService:

    async def store_file(self, storage_id: str, file_data: bytes) -> str:
        """
        Store a file in the storage system.
        Already reads all data into memory, so not suitable for large files.

        :param storage_id: Unique identifier for the file in the storage system.
        :param file_data: The binary data of the file to be stored.
        :return: The SHA-256 hash of the stored file as a hex string.
        """
        raise NotImplementedError
    
    async def store_file_from_uploadfile(self, storage_id: str, upload_file: UploadFile) -> str:
        """
        Stream the UploadFile (async) to a temp file while computing SHA-256, then persist it.
        More memory efficient for large files than reading all into memory first (store_file).

        :param storage_id: Unique identifier for the file in the storage system.
        :param upload_file: The UploadFile instance from FastAPI.
        :return: The SHA-256 hash of the stored file as a hex string.
        """
        raise NotImplementedError

    async def retrieve_file(self, storage_id: str) -> AsyncIterator[bytes]:
        """
        Retrieve a file from the storage system as an async iterator of decompressed chunks.

        :param storage_id: Unique identifier for the file in the storage system.
        :return: Async iterator yielding decompressed bytes chunks.
        """
        raise NotImplementedError
    
    async def delete_file(self, storage_id: str) -> None:
        """
        Delete a file from the storage system.

        :param storage_id: Unique identifier for the file in the storage system.
        """
        raise NotImplementedError


class LocalFileStorageServiceImpl(FileStorageService):
    """
    Local file storage implementation for testing purposes.
    """

    def __init__(self):
        self.documents_path = TMP_PATH / "documents"
        if not self.documents_path.exists():
            self.documents_path.mkdir(parents=True, exist_ok=True)

    async def store_file(self, storage_id: str, file_data: bytes) -> None:
        file_path = self.documents_path / storage_id
        if file_path.exists():
            raise ConflictException(f"File with ID '{storage_id}' already exists.")

        try:
            split = storage_id.split('/')
            if len(split) == 2:
                # Create pid prefix directory if it doesn't exist
                prefix_dir = self.documents_path / split[0]
                if not prefix_dir.exists():
                    prefix_dir.mkdir(parents=True, exist_ok=True)
            elif len(split) > 2:
                raise Exception("Invalid file path structure.")

            # Compress the provided bytes with zstd before persisting
            cctx = zstd.ZstdCompressor(level=ZSTD_LEVEL)
            compressed_data = cctx.compress(file_data)

            with open(file_path, 'wb') as f:
                f.write(compressed_data)

            # Return SHA-256 computed on original (uncompressed) bytes
            return hashlib.sha256(file_data).hexdigest()
        except Exception as e:
            logger.error(f"Error storing file {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to store file.")
        
    async def store_file_from_uploadfile(self, storage_id: str, upload_file: UploadFile) -> str:
        file_path = self.documents_path / storage_id
        if file_path.exists():
            raise ConflictException(f"File with ID '{storage_id}' already exists.")

        # stream, hash and compress into a temp file
        hasher = hashlib.sha256()
        tmp_path = None

        try:
            # create a temporary file path
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name
                # prepare zstd stream compressor
                cctx = zstd.ZstdCompressor(level=ZSTD_LEVEL)
                cobj = cctx.compressobj()

                # read in chunks from UploadFile (async) and write compressed bytes synchronously
                while True:
                    chunk = await upload_file.read(READ_CHUNK)  # async read
                    if not chunk:
                        break
                    hasher.update(chunk)           # update hash on original bytes
                    compressed = cobj.compress(chunk)
                    if compressed:
                        tmp.write(compressed)

                # flush compressor and write remainder
                tail = cobj.flush()
                if tail:
                    tmp.write(tail)

            # compute hash of original data
            hash_hex = hasher.hexdigest()

            split = storage_id.split('/')
            if len(split) == 2:
                # Create pid prefix directory if it doesn't exist
                prefix_dir = self.documents_path / split[0]
                if not prefix_dir.exists():
                    prefix_dir.mkdir(parents=True, exist_ok=True)
            elif len(split) > 2:
                # cleanup temp before raising
                try:
                    if tmp_path:
                        os.unlink(tmp_path)
                except Exception:
                    pass
                raise Exception("Invalid file path structure")

            # Move temp (compressed) file to final location
            os.rename(tmp_path, file_path)
            tmp_path = None  # prevent deletion in finally

            return hash_hex

        except Exception as e:
            logger.error(f"Error storing file {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to store file.")
        finally:
            # cleanup temp file if present
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    async def retrieve_file(self, storage_id: str) -> AsyncIterator[bytes]:
        file_path = self.documents_path / storage_id
        if not file_path.exists():
            raise NotFoundException(f"File with ID '{storage_id}' not found.")

        try:
            # stream read compressed file and decompress incrementally to avoid loading whole file
            dctx = zstd.ZstdDecompressor()
            dobj = dctx.decompressobj()

            async with aiofiles.open(file_path, 'rb') as f:
                while True:
                    comp_chunk = await f.read(READ_CHUNK)
                    if not comp_chunk:
                        break
                    decompressed = dobj.decompress(comp_chunk)
                    if decompressed:
                        yield decompressed

                # flush any remaining decompressed bytes
                tail = dobj.flush()
                if tail:
                    yield tail

        except Exception as e:
            logger.error(f"Error retrieving file {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to retrieve file.")
        
    async def delete_file(self, storage_id: str) -> None:
        file_path = self.documents_path / storage_id
        if not file_path.exists():
            return  # If the file doesn't exist, consider it already deleted

        try:
            file_path.unlink()
            # Optionally, remove the prefix directory if empty
            split = storage_id.split('/')
            if len(split) == 2:
                prefix_dir = self.documents_path / split[0]
                if prefix_dir.exists() and not any(prefix_dir.iterdir()):
                    prefix_dir.rmdir()
        except Exception as e:
            logger.error(f"Error deleting file {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to delete file.")


class MinioFileStorageServiceImpl(FileStorageService):
    """
    MinIO-backed file storage implementation.
    Expects the following settings to be available (with sensible defaults for local dev):
      - MINIO_ENDPOINT (default: "yprovstore-minio:9000")
      - MINIO_ACCESS_KEY (default: "minioadmin")
      - MINIO_SECRET_KEY (default: "minioadmin")
      - MINIO_BUCKET (default: "yprov-documents")
      - MINIO_SECURE (default: True)
      - MINIO_REGION (optional)
    """

    def __init__(self):
        # Lazy import of MinIO client to avoid hard dependency when using local storage
        try:
            minio_module = importlib.import_module("minio")
            minio_error_module = importlib.import_module("minio.error")
            MinioClient = getattr(minio_module, "Minio")
            self._S3Error = getattr(minio_error_module, "S3Error")
        except Exception:  # pragma: no cover
            raise ServiceUnavailableException(
                "MinIO client not installed. Please add 'minio' to dependencies to use MinIO storage.")

        self.bucket = settings.MINIO_BUCKET
        self.client = MinioClient(
            settings.MINIO_ENDPOINT, access_key=settings.MINIO_ACCESS_KEY, secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE, region=settings.MINIO_REGION
        )

        # Ensure bucket exists
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except Exception as e:
            # If it's an S3 error and not auth/permission, still propagate as service unavailable
            logger.error(f"Error ensuring bucket '{self.bucket}': {e}")
            raise ServiceUnavailableException("Failed to ensure storage bucket.")

    async def store_file(self, storage_id: str, file_data: bytes) -> None:
        # Check for conflict
        try:
            self.client.stat_object(self.bucket, storage_id)
            # If stat succeeds, object exists
            raise ConflictException(f"File with ID '{storage_id}' already exists.")
        except Exception as e:
            if isinstance(e, getattr(self, "_S3Error", tuple())):
                if getattr(e, "code", "") not in ("NoSuchKey", "NoSuchObject", "NotFound"):
                    logger.error(f"MinIO stat_object error for {storage_id}: {e}")
                    raise ServiceUnavailableException("Failed to access storage.")
            else:
                logger.warning(f"Unexpected error during stat_object for {storage_id}: {e}. Proceeding to upload.")

        try:
            # Compress the provided bytes with zstd to reduce upload size
            cctx = zstd.ZstdCompressor(level=ZSTD_LEVEL)
            compressed_data = cctx.compress(file_data)

            # Compute hash over original bytes (keeps behaviour consistent with other methods)
            file_hash = hashlib.sha256(file_data).hexdigest()

            # Upload compressed payload, include metadata about original hash and compression
            compressed_stream = io.BytesIO(compressed_data)
            self.client.put_object(
                self.bucket,
                storage_id,
                data=compressed_stream,
                length=len(compressed_data),
                content_type="application/octet-stream",
                metadata={"sha256": file_hash, "compression": "zstd"}
            )
            return file_hash
        except Exception as e:
            if isinstance(e, getattr(self, "_S3Error", tuple())):
                logger.error(f"MinIO put_object error for {storage_id}: {e}")
                raise ServiceUnavailableException("Failed to store file.")
            logger.error(f"Unexpected error storing file {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to store file.")

    async def store_file_from_uploadfile(self, storage_id: str, upload_file: UploadFile) -> str:
        # Check for conflict
        try:
            self.client.stat_object(self.bucket, storage_id)
            # If stat succeeds, object exists
            raise ConflictException(f"File with ID '{storage_id}' already exists.")
        except Exception as e:
            if isinstance(e, getattr(self, "_S3Error", tuple())):
                if getattr(e, "code", "") not in ("NoSuchKey", "NoSuchObject", "NotFound"):
                    logger.error(f"MinIO stat_object error for {storage_id}: {e}")
                    raise ServiceUnavailableException("Failed to access storage.")
            else:
                logger.warning(f"Unexpected error during stat_object for {storage_id}: {e}. Proceeding to upload.")

        # stream and hash into a temp file
        hasher = hashlib.sha256()
        tmp_path = None

        # compression params
        

        # NOTE: writing compressed bytes to disk; aiofiles performs non-blocking writes
        try:
            # create a temporary file path
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name

            # streaming read (async) -> compress -> async write (aiofiles)
            cctx = zstd.ZstdCompressor(level=ZSTD_LEVEL)
            cobj = cctx.compressobj()

            async with aiofiles.open(tmp_path, "wb") as f:
                while True:
                    chunk = await upload_file.read(READ_CHUNK)  # async read
                    if not chunk:
                        break
                    # update hash on original bytes
                    hasher.update(chunk)
                    # compress incrementally
                    compressed = cobj.compress(chunk)
                    if compressed:
                        await f.write(compressed)

                # flush compressor and write remainder
                tail = cobj.flush()
                if tail:
                    await f.write(tail)

            # compute meta and compressed size
            hash_hex = hasher.hexdigest()
            compressed_size = os.path.getsize(tmp_path)

            # The blocking put_object call in a thread pool to avoid blocking loop
            loop = asyncio.get_running_loop()

            def upload_sync():
                # open file and call blocking minio put_object inside the executor thread
                with open(tmp_path, "rb") as data_stream:
                    metadata = {"sha256": hash_hex, "compression": "zstd"}
                    self.client.put_object(
                        self.bucket,
                        storage_id,
                        data=data_stream,
                        length=compressed_size,
                        content_type=upload_file.content_type or "application/octet-stream",
                        metadata=metadata,
                    )

            await loop.run_in_executor(None, upload_sync)

            return hash_hex

        except Exception as e:
            logger.exception(f"Error storing file {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to store file.")
        finally:
            # cleanup temp file if present
            logger.info(f"Cleaning up temp file {tmp_path}")
            # if tmp_path:
            #     try:
            #         os.unlink(tmp_path)
            #     except Exception:
            #         pass

    async def retrieve_file(self, storage_id: str) -> AsyncIterator[bytes]:
        """
        Retrieve a file from MinIO as an async iterator of (decompressed) chunks.
        """
        # check metadata first to decide whether to decompress
        try:
            try:
                stat = self.client.stat_object(self.bucket, storage_id)
                # metadata keys can be present as provided or prefixed; check both
                meta = getattr(stat, "metadata", {}) or {}
                compression_meta = meta.get("compression") or meta.get("x-amz-meta-compression")
            except Exception as e:
                # map not found
                if isinstance(e, getattr(self, "_S3Error", tuple())) and getattr(e, "code", "") in ("NoSuchKey", "NoSuchObject", "NotFound"):
                    raise NotFoundException(f"File with ID '{storage_id}' not found.")
                # if stat_object failed for other reasons, log and proceed to attempt get_object (best-effort)
                logger.warning(f"Unexpected error during stat_object for {storage_id}: {e}. Proceeding to get_object.")
                compression_meta = None

            response = self.client.get_object(self.bucket, storage_id)
        except Exception as e:
            if isinstance(e, getattr(self, "_S3Error", tuple())):
                if getattr(e, "code", "") in ("NoSuchKey", "NoSuchObject", "NotFound"):
                    raise NotFoundException(f"File with ID '{storage_id}' not found.")
                logger.error(f"MinIO get_object/stat_object error for {storage_id}: {e}")
                raise ServiceUnavailableException("Failed to retrieve file.")
            logger.error(f"Unexpected error retrieving file {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to retrieve file.")

        # stream read in executor to avoid blocking loop
        loop = asyncio.get_running_loop()
        dctx = None
        dobj = None
        try:
            is_zstd = (compression_meta and str(compression_meta).lower() == "zstd")
            if is_zstd:
                dctx = zstd.ZstdDecompressor()
                dobj = dctx.decompressobj()
            else:
                logger.warning(f"File {storage_id} does not indicate zstd compression; not decompressing.")

            while True:
                # perform blocking read in executor
                comp_chunk = await loop.run_in_executor(None, response.read, READ_CHUNK)
                if not comp_chunk:
                    break

                if is_zstd:
                    out = dobj.decompress(comp_chunk)
                    if out:
                        yield out
                else:
                    yield comp_chunk

            if is_zstd:
                tail = dobj.flush()
                if tail:
                    yield tail

        finally:
            try:
                response.close()
                response.release_conn()
            except Exception:
                pass
        

    async def delete_file(self, storage_id: str) -> None:
        try:
            self.client.remove_object(self.bucket, storage_id)
        except Exception as e:
            if isinstance(e, getattr(self, "_S3Error", tuple())):
                # If not found, consider it already deleted
                if getattr(e, "code", "") in ("NoSuchKey", "NoSuchObject", "NotFound"):
                    return
                logger.error(f"MinIO remove_object error for {storage_id}: {e}")
                raise ServiceUnavailableException("Failed to delete stored file.")
            logger.error(f"Unexpected error deleting file {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to delete stored file.")


class FileStorageServiceProvider(Provider):
    """
    Provider for the FileStorageService. Selects Local or MinIO backend
    based on USE_LOCAL_FILE_STORAGE_SERVICE (default True for local dev).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(scope=Scope.APP, *args, **kwargs)
        self.use_local: bool = settings.USE_LOCAL_FILE_STORAGE_SERVICE
        if self.use_local:
            logger.warning("Using local file storage backend (filesystem under tmp/documents)")
        else:
            logger.info("Using MinIO file storage backend")

    @provide
    def file_storage_service(self) -> FileStorageService:
        if self.use_local:
            return LocalFileStorageServiceImpl()
        return MinioFileStorageServiceImpl()
    

class CompressionServiceProvider(Provider):
    """
    Provider for the CompressionService. Currently only Zstd is supported.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(scope=Scope.APP, *args, **kwargs)

    @provide
    def compression_service(self) -> zstd:
        # Currently only Zstd is supported; could be extended in future
        return zstd
