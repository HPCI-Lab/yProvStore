import io
import os
import hashlib
import asyncio
import logging
import tempfile
import importlib
from typing import AsyncIterator
from urllib.parse import urlparse, urlunparse

import aiofiles
from fastapi import UploadFile

from application import settings
from application.settings import TMP_PATH
from application.exceptions.types import ConflictException, NotFoundException, ServiceUnavailableException

from .service import FileStorageService, CompressionService, DocumentNotCompressedException


logger = logging.getLogger(__name__)


READ_CHUNK = 1024 * 1024  # 1 MiB read chunks for streaming


class LocalFileStorageServiceImpl(FileStorageService):
    """
    Local file storage implementation for testing purposes.
    """

    def __init__(self, compression_service: CompressionService | None = None, bucket: str | None = None):
        self.documents_path = TMP_PATH / (bucket or "documents")
        if not self.documents_path.exists():
            self.documents_path.mkdir(parents=True, exist_ok=True)
        self.compression_service = compression_service
        self.COMPRESSION_STANDARD = super().get_compression_standard()

    async def store_file(self, storage_id: str, file_data: bytes, skip_compression: bool = False, ignore_compression: bool = False, bucket: str | None = None) -> None:
        if ignore_compression and skip_compression:
            raise ValueError("Cannot set both ignore_compression and skip_compression to True.")
        bucket_path = TMP_PATH / bucket if bucket else self.documents_path
        if not bucket_path.exists():
            bucket_path.mkdir(parents=True, exist_ok=True)
        file_path = bucket_path / storage_id
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
                # recursively create directories if needed
                dir_path = self.documents_path
                for part in split[:-1]:
                    dir_path = dir_path / part
                    if not dir_path.exists():
                        dir_path.mkdir(parents=True, exist_ok=True)

            if ignore_compression:
                logger.debug(f"Ignoring compression for file {storage_id}")
                with open(file_path, 'wb') as f:
                    f.write(file_data)
                # Return SHA-256 computed on original (uncompressed) bytes
                return hashlib.sha256(file_data).hexdigest()
            
            # Compress the provided bytes before persisting
            if skip_compression:
                logger.debug(f"Skipping compression for file {storage_id}")
                uncompressed_data = self.compression_service.get_decompressor(self.COMPRESSION_STANDARD).decompress(file_data)
                uncompressed_data += self.compression_service.get_decompressor(self.COMPRESSION_STANDARD).flush_decompression()
                data_to_store = file_data
            else:
                data_to_store = self.compression_service.get_compressor(self.COMPRESSION_STANDARD).compress(file_data)
                data_to_store += self.compression_service.get_compressor(self.COMPRESSION_STANDARD).flush_compression()
                logger.info(f"File {storage_id} compressed from {len(file_data)} to {len(data_to_store)} bytes.")
                uncompressed_data = file_data

            with open(file_path, 'wb') as f:
                f.write(data_to_store)

            # Return SHA-256 computed on original (uncompressed) bytes
            return hashlib.sha256(uncompressed_data).hexdigest()
        except Exception as e:
            logger.error(f"Error storing file {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to store file.")

    async def store_file_from_uploadfile(self, storage_id: str, upload_file: UploadFile, skip_compression: bool = False, ignore_compression: bool = False, bucket: str | None = None) -> str:
        if ignore_compression and skip_compression:
            raise ValueError("Cannot set both ignore_compression and skip_compression to True.")
        bucket_path = TMP_PATH / bucket if bucket else self.documents_path
        if not bucket_path.exists():
            bucket_path.mkdir(parents=True, exist_ok=True)
        file_path = bucket_path / storage_id
        if file_path.exists():
            raise ConflictException(f"File with ID '{storage_id}' already exists.")

        # stream, hash and compress into a temp file
        hasher = hashlib.sha256()
        tmp_path = None

        try:
            # create a temporary file path
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name
                decompressor = None
                compressor = None
                if not ignore_compression and skip_compression:
                    logger.debug(f"Skipping compression for file {storage_id}")
                    # prepare stream decompressor to compute hash on original bytes
                    decompressor = self.compression_service.get_decompressor(self.COMPRESSION_STANDARD)
                elif not ignore_compression:
                    # prepare stream compressor
                    compressor = self.compression_service.get_compressor(self.COMPRESSION_STANDARD)

                # read in chunks from UploadFile (async) and write compressed bytes synchronously
                while True:
                    chunk = await upload_file.read(READ_CHUNK)  # async read
                    if not chunk:
                        break
                    original_chunk = chunk
                    if not ignore_compression and skip_compression:
                        # decompress to get original bytes for hashing
                        original_chunk = decompressor.decompress(chunk)
                    hasher.update(original_chunk)           # update hash on original bytes
                    chunk_to_store = compressor.compress(chunk) if compressor else chunk
                    if chunk_to_store:
                        tmp.write(chunk_to_store)

                # flush compressor and write remainder
                tail = compressor.flush_compression() if compressor else b''
                if tail:
                    tmp.write(tail)

                if decompressor:
                    # flush decompressor to complete hash computation
                    tail = decompressor.flush_decompression()
                    if tail:
                        hasher.update(tail)

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

    async def retrieve_file(self, storage_id: str, skip_decompression: bool = False, ignore_compression: bool = False, bucket: str | None = None) -> AsyncIterator[bytes]:
        if ignore_compression and skip_decompression:
            raise ValueError("Cannot set both ignore_compression and skip_decompression to True.")
        bucket_path = TMP_PATH / bucket if bucket else self.documents_path
        file_path = bucket_path / storage_id
        if not file_path.exists():
            raise NotFoundException(f"File with ID '{storage_id}' not found.")

        try:
            decompressor = None
            if not ignore_compression:
                # Peek at the start of the file to check for compression
                async with aiofiles.open(file_path, 'rb') as fpeek:
                    head = await fpeek.read(4)
                compression_standard = self.compression_service.detect_compression(None, head)
                
                if skip_decompression:
                    if not compression_standard:
                        raise DocumentNotCompressedException("Document is not compressed.")
                    logger.debug(f"Skipping decompression for file {storage_id}.")
                    compression_standard = None

                decompressor = self.compression_service.get_decompressor(compression_standard) if compression_standard else None

            if decompressor:
                logger.debug(f"File {storage_id} is {compression_standard.value}-compressed; decompressing on-the-fly.")
                # stream read compressed file and decompress incrementally to avoid loading whole file
                async with aiofiles.open(file_path, 'rb') as f:
                    while True:
                        comp_chunk = await f.read(READ_CHUNK)
                        if not comp_chunk:
                            break
                        decompressed = decompressor.decompress(comp_chunk)
                        if decompressed:
                            yield decompressed

                    # flush any remaining decompressed bytes
                    tail = decompressor.flush_decompression()
                    if tail:
                        yield tail
            else:
                if not skip_decompression and not ignore_compression:
                    logger.warning(f"File {storage_id} does not indicate compression; streaming raw bytes.")
                # file is not compressed: stream raw bytes
                async with aiofiles.open(file_path, 'rb') as f:
                    while True:
                        chunk = await f.read(READ_CHUNK)
                        if not chunk:
                            break
                        yield chunk

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
        
    async def get_upload_presigned_url(self, **kwargs) -> str:
        raise NotImplementedError("Presigned URLs are not supported in local storage mode.")
    
    async def get_download_presigned_url(self, **kwargs) -> str:
        raise NotImplementedError("Presigned URLs are not supported in local storage mode.")


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

    def __init__(self, compression_service: CompressionService | None = None, bucket: str | None = None):
        self.compression_service = compression_service
        # Lazy import of MinIO client to avoid hard dependency when using local storage
        try:
            minio_module = importlib.import_module("minio")
            minio_error_module = importlib.import_module("minio.error")
            MinioClient = getattr(minio_module, "Minio")
            self._S3Error = getattr(minio_error_module, "S3Error")
        except Exception:  # pragma: no cover
            raise ServiceUnavailableException(
                "MinIO client not installed. Please add 'minio' to dependencies to use MinIO storage.")
        self.COMPRESSION_STANDARD = super().get_compression_standard()

        self.bucket = bucket or settings.MINIO_BUCKET
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

    async def store_file(self, storage_id: str, file_data: bytes, skip_compression: bool = False, ignore_compression: bool = False, bucket: str | None = None) -> None:
        if ignore_compression and skip_compression:
            raise ValueError("Cannot set both ignore_compression and skip_compression to True.")
        # Check for conflict
        try:
            self.client.stat_object(bucket or self.bucket, storage_id)
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
            if not ignore_compression and skip_compression:
                logger.debug(f"Skipping compression for file {storage_id}")
                data_to_store = file_data
                original_data = self.compression_service.get_decompressor(self.COMPRESSION_STANDARD).decompress(file_data)
            elif not ignore_compression:
                # Compress the provided bytes to reduce upload size
                data_to_store = self.compression_service.get_compressor(self.COMPRESSION_STANDARD).compress(file_data)
                original_data = file_data
            else:
                logger.debug(f"Ignoring compression for file {storage_id}")
                data_to_store = file_data
                original_data = file_data

            # Compute hash over original bytes (keeps behaviour consistent with other methods)
            file_hash = hashlib.sha256(original_data).hexdigest()

            # Upload compressed payload, include metadata about original hash and compression
            compressed_stream = io.BytesIO(data_to_store)
            compression_meta = {"compression": self.COMPRESSION_STANDARD.value} if not skip_compression and not ignore_compression else {}
            self.client.put_object(
                bucket or self.bucket,
                storage_id,
                data=compressed_stream,
                length=len(data_to_store),
                content_type="application/octet-stream",
                metadata={"sha256": file_hash, **compression_meta},
            )
            return file_hash
        except Exception as e:
            if isinstance(e, getattr(self, "_S3Error", tuple())):
                logger.error(f"MinIO put_object error for {storage_id}: {e}")
                raise ServiceUnavailableException("Failed to store file.")
            logger.error(f"Unexpected error storing file {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to store file.")

    async def store_file_from_uploadfile(self, storage_id: str, upload_file: UploadFile, skip_compression: bool = False, ignore_compression: bool = False, bucket: str | None = None) -> str:
        if ignore_compression and skip_compression:
            raise ValueError("Cannot set both ignore_compression and skip_compression to True.")
        # Check for conflict
        try:
            self.client.stat_object(bucket or self.bucket, storage_id)
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

        # NOTE: writing compressed bytes to disk; aiofiles performs non-blocking writes
        try:
            # create a temporary file path
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name

            compressor = None
            decompressor = None
            if not ignore_compression and skip_compression:
                logger.debug(f"Skipping compression for file {storage_id}")
                # prepare stream decompressor to compute hash on original bytes
                decompressor = self.compression_service.get_decompressor(self.COMPRESSION_STANDARD)
            elif not ignore_compression:
                # streaming read (async) -> compress -> async write (aiofiles)
                compressor = self.compression_service.get_compressor(self.COMPRESSION_STANDARD)

            async with aiofiles.open(tmp_path, "wb") as f:
                while True:
                    chunk = await upload_file.read(READ_CHUNK)  # async read
                    if not chunk:
                        break
                    # update hash on original bytes
                    original_chunk = chunk
                    if not ignore_compression and skip_compression:
                        original_chunk = decompressor.decompress(chunk)
                    hasher.update(original_chunk)
                    # compress incrementally
                    data_to_store = compressor.compress(chunk) if compressor else chunk
                    if data_to_store:
                        await f.write(data_to_store)

                # flush compressor and write remainder
                tail = compressor.flush_compression() if compressor else b''
                if tail:
                    await f.write(tail)

                if decompressor:
                    # flush decompressor to complete hash computation
                    tail = decompressor.flush_decompression()
                    if tail:
                        hasher.update(tail)

            # compute meta and compressed size
            hash_hex = hasher.hexdigest()
            compressed_size = os.path.getsize(tmp_path)

            # The blocking put_object call in a thread pool to avoid blocking loop
            loop = asyncio.get_running_loop()

            compression_meta = {"compression": self.COMPRESSION_STANDARD.value} if not skip_compression else {}
            def upload_sync():
                # open file and call blocking minio put_object inside the executor thread
                with open(tmp_path, "rb") as data_stream:
                    metadata = {"sha256": hash_hex, **compression_meta}
                    self.client.put_object(
                        bucket or self.bucket,
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
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    async def retrieve_file(self, storage_id: str, skip_decompression: bool = False, ignore_compression: bool = False, bucket: str | None = None) -> AsyncIterator[bytes]:
        """
        Retrieve a file from MinIO as an async iterator of (decompressed) chunks.
        """
        if ignore_compression and skip_decompression:
            raise ValueError("Cannot set both ignore_compression and skip_decompression to True.")
        # check metadata first to decide whether to decompress
        try:
            if ignore_compression:
                compression_meta = None
            else:
                try:
                    stat = self.client.stat_object(bucket or self.bucket, storage_id)
                    # metadata keys can be present as provided or prefixed; check both
                    meta = getattr(stat, "metadata", {}) or {}
                    compression_str = meta.get("compression") or meta.get("x-amz-meta-compression")
                    compression_meta = {"compression": compression_str} if compression_str else None
                except Exception as e:
                    # map not found
                    if isinstance(e, getattr(self, "_S3Error", tuple())) and getattr(e, "code", "") in ("NoSuchKey", "NoSuchObject", "NotFound"):
                        raise NotFoundException(f"File with ID '{storage_id}' not found.")
                    # if stat_object failed for other reasons, log and proceed to attempt get_object (best-effort)
                    logger.warning(f"Unexpected error during stat_object for {storage_id}: {e}. Proceeding to get_object.")
                    compression_meta = None

            response = self.client.get_object(bucket or self.bucket, storage_id)
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
        try:
            decompressor = None
            if not ignore_compression:
                compression_standard = self.compression_service.detect_compression(compression_meta, None)
                decompressor = self.compression_service.get_decompressor(compression_standard) if compression_standard else None
                if skip_decompression:
                    if not decompressor:
                        raise DocumentNotCompressedException("Document is not compressed.")
                    logger.debug(f"Skipping decompression for file {storage_id}.")
                    decompressor = None
                elif not decompressor:
                    logger.warning(f"File {storage_id} does not indicate compression meta; not decompressing.")

            while True:
                # perform blocking read in executor
                comp_chunk = await loop.run_in_executor(None, response.read, READ_CHUNK)
                if not comp_chunk:
                    break

                if decompressor:
                    out = decompressor.decompress(comp_chunk)
                    if out:
                        yield out
                else:
                    yield comp_chunk

            if decompressor:
                tail = decompressor.flush_decompression()
                if tail:
                    yield tail

        finally:
            try:
                response.close()
                response.release_conn()
            except Exception:
                pass
        
    async def delete_file(self, storage_id: str, bucket: str | None = None) -> None:
        try:
            self.client.remove_object(bucket or self.bucket, storage_id)
        except Exception as e:
            if isinstance(e, getattr(self, "_S3Error", tuple())):
                # If not found, consider it already deleted
                if getattr(e, "code", "") in ("NoSuchKey", "NoSuchObject", "NotFound"):
                    return
                logger.error(f"MinIO remove_object error for {storage_id}: {e}")
                raise ServiceUnavailableException("Failed to delete stored file.")
            logger.error(f"Unexpected error deleting file {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to delete stored file.")

    async def get_upload_presigned_url(self, storage_id: str, expiration_seconds: int = 3600, bucket: str | None = None, public_endpoint: str | None = None) -> str:
        try:
            url = self.client.presigned_put_object(
                bucket or self.bucket,
                storage_id,
                expires=expiration_seconds
            )
            if public_endpoint:
                # replace the endpoint with the public one
                parsed_url = urlparse(url)
                
                # Ensure public_endpoint has a scheme
                if not public_endpoint.startswith(('http://', 'https://')):
                    # Use the same scheme as the original URL
                    public_endpoint = f"{parsed_url.scheme}://{public_endpoint}"
                
                public_parsed = urlparse(public_endpoint)
                new_url = parsed_url._replace(scheme=public_parsed.scheme, netloc=public_parsed.netloc)
                return urlunparse(new_url)
            return url
        except Exception as e:
            logger.error(f"Error generating upload presigned URL for {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to generate upload presigned URL.")
        
    async def get_download_presigned_url(self, storage_id: str, expiration_seconds: int = 3600, bucket: str | None = None, public_endpoint: str | None = None) -> str:
        try:
            url = self.client.presigned_get_object(
                bucket or self.bucket,
                storage_id,
                expires=expiration_seconds
            )
            if public_endpoint:
                # replace the endpoint with the public one
                parsed_url = urlparse(url)
                
                # Ensure public_endpoint has a scheme
                if not public_endpoint.startswith(('http://', 'https://')):
                    # Use the same scheme as the original URL
                    public_endpoint = f"{parsed_url.scheme}://{public_endpoint}"
                
                public_parsed = urlparse(public_endpoint)
                new_url = parsed_url._replace(scheme=public_parsed.scheme, netloc=public_parsed.netloc)
                return urlunparse(new_url)
            return url
        except Exception as e:
            logger.error(f"Error generating download presigned URL for {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to generate download presigned URL.")
