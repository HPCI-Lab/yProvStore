import logging
from enum import Enum
from typing import AsyncIterator

from fastapi import UploadFile
from dishka import Provider, provide, Scope
from sqlalchemy.ext.asyncio import AsyncSession as SessionType

from application import settings
from models.artifact import PresignedURL, PresignedURLOperationType


logger = logging.getLogger(__name__)


class CompressionStandard(Enum):
    ZSTD = "zstd"


class DocumentNotCompressedException(Exception):
    """Raised when a document is expected to be compressed but is not."""
    pass


class FileStorageService:

    async def store_file(self, storage_id: str, file_data: bytes, skip_compression: bool = False, ignore_compression: bool = False, bucket: str | None = None) -> str:
        """
        Store a file in the storage system.
        Already reads all data into memory, so not suitable for large files.

        :param storage_id: Unique identifier for the file in the storage system.
        :param file_data: The binary data of the file to be stored.
        :param skip_compression: If True, store without compressing the file. If enabled, the document
                                 will be still be uncompressed on-the-fly just to compute the hash.
                                 Therefore, the document must be compressed according to the supported compression standard.
        :param ignore_compression: If True, ignore compression mechanism entirely and store as-is.
        :param bucket: Optional bucket name for storage backends that support multiple buckets.
        :return: The SHA-256 hash of the stored file as a hex string.
        """
        raise NotImplementedError

    async def store_file_from_uploadfile(self, storage_id: str, upload_file: UploadFile, skip_compression: bool = False, ignore_compression: bool = False, bucket: str | None = None) -> str:
        """
        Stream the UploadFile (async) to a temp file while computing SHA-256, then persist it.
        More memory efficient for large files than reading all into memory first (store_file).

        :param storage_id: Unique identifier for the file in the storage system.
        :param upload_file: The UploadFile instance from FastAPI.
        :param skip_compression: If True, store without compressing the file. If enabled, the document 
                                 will be still be uncompressed on-the-fly just to compute the hash.
                                 Therefore, the document must be compressed according to the supported compression standard.
        :param ignore_compression: If True, ignore compression mechanism entirely and store as-is.
        :param bucket: Optional bucket name for storage backends that support multiple buckets.
        :return: The SHA-256 hash of the stored file as a hex string.
        """
        raise NotImplementedError
    
    async def get_file_size(self, storage_id: str, compressed: bool = False, bucket: str | None = None) -> int:
        """
        Get the size of a file in the storage system.

        :param storage_id: Unique identifier for the file in the storage system.
        :param compressed: If False (default), returns the uncompressed (original) size if available.
                          If True, returns the compressed (stored) size.
        :param bucket: Optional bucket name for storage backends that support multiple buckets.
        :return: Size of the file in bytes.
        
        Note:
            For implementations that don't track uncompressed size, this may return
            the stored size regardless of the compressed parameter.
        """
        raise NotImplementedError

    async def retrieve_file(self, storage_id: str, skip_decompression: bool = False, ignore_compression: bool = False, bucket: str | None = None) -> AsyncIterator[bytes]:
        """
        Retrieve a file from the storage system as an async iterator of decompressed chunks.

        :param storage_id: Unique identifier for the file in the storage system.
        :param skip_decompression: If True, stream without decompressing the file.
        :param ignore_compression: If True, ignore compression mechanism entirely and retrieve as-is.
        :raise DocumentNotCompressedException: If skip_decompression is True but the document is not compressed.
        :param bucket: Optional bucket name for storage backends that support multiple buckets.
        :return: Async iterator yielding decompressed bytes chunks.
        """
        raise NotImplementedError
    
    async def delete_file(self, storage_id: str, bucket: str | None = None) -> None:
        """
        Delete a file from the storage system.

        :param storage_id: Unique identifier for the file in the storage system.
        :param bucket: Optional bucket name for storage backends that support multiple buckets.
        """
        raise NotImplementedError

    async def get_upload_presigned_url(self, storage_id: str, expiration_seconds: int = 3600, bucket: str | None = None, public_endpoint: str | None = None) -> str:
        """
        Generate a presigned URL for uploading a file directly to the storage system.
        This method will raise NotImplementedError if the storage backend does not support presigned URLs.
        As such, manage proxy artifact storage accordingly before calling this method.

        :param storage_id: Unique identifier for the file in the storage system.
        :param expiration_seconds: Time in seconds for which the presigned URL is valid.
        :param bucket: Optional bucket name for storage backends that support multiple buckets.
        :param public_endpoint: Optional public endpoint to use in the presigned URL instead of the default storage endpoint.
        :return: Presigned URL as a string.
        """
        raise NotImplementedError

    async def get_download_presigned_url(self, storage_id: str, expiration_seconds: int = 3600, bucket: str | None = None, public_endpoint: str | None = None) -> str:
        """
        Generate a presigned URL for downloading a file directly from the storage system.
        This method will raise NotImplementedError if the storage backend does not support presigned URLs.
        As such, manage proxy artifact storage accordingly before calling this method.

        :param storage_id: Unique identifier for the file in the storage system.
        :param expiration_seconds: Time in seconds for which the presigned URL is valid.
        :param bucket: Optional bucket name for storage backends that support multiple buckets.
        :param public_endpoint: Optional public endpoint to use in the presigned URL instead of the default storage endpoint.
        :return: Presigned URL as a string.
        """
        raise NotImplementedError

    @staticmethod
    def get_compression_standard() -> CompressionStandard:
        """
        Get the default compression standard used by the service.

        :return: CompressionStandard enum value.
        """
        return CompressionStandard.ZSTD
    

class ArtifactFileStorageService(FileStorageService):
    """
    Specialized FileStorageService for artifact files.
    Allows to define a different bucket name for artifact storage.
    """
    pass


class Compressor:
    """
    Interface for a compressor/decompressor.
    """

    def compress(self, data: bytes) -> bytes:
        """
        Compress the given data.

        :param data: Data to be compressed.
        :return: Compressed data.
        """
        raise NotImplementedError

    def decompress(self, data: bytes) -> bytes:
        """
        Decompress the given data.

        :param data: Data to be decompressed.
        :return: Decompressed data.
        """
        raise NotImplementedError
    
    def flush_compression(self) -> bytes:
        """
        Flush any remaining compressed data.

        :return: Remaining compressed data.
        """
        raise NotImplementedError
    
    def flush_decompression(self) -> bytes:
        """
        Flush any remaining decompressed data.

        :return: Remaining decompressed data.
        """
        raise NotImplementedError
    

class CompressionService:
    
    def get_compressor(self, compression_standard: CompressionStandard) -> Compressor:
        """
        Get a compressor instance for compressing data.

        :param compression_standard: The compression standard to use.
        :return: Compressor instance.
        """
        raise NotImplementedError
    
    def get_decompressor(self, compression_standard: CompressionStandard) -> Compressor:
        """
        Get a decompressor instance for decompressing data.

        :param compression_standard: The compression standard to use.
        :return: Decompressor instance.
        """
        raise NotImplementedError
    
    def detect_compression(self, compression_meta: dict | None = None, data_chunk: bytes | None = None) -> CompressionStandard | None:
        """
        Detect the compression standard used based on metadata or data chunk.

        :param compression_meta: Optional metadata indicating compression.
        :param data_chunk: Optional initial data chunk to inspect for compression standard.
        :return: Detected CompressionStandard or None if uncompressed.
        """
        raise NotImplementedError


class PresignedURLService:
    """
    Service for generating and storing presigned URLs on for proxy artifact storage.
    """
    
    async def generate_presigned_url(self, user_id: str, storage_id: str, operation_type: PresignedURLOperationType, filename: str, expires_in: int = 3600) -> PresignedURL:
        """
        Generate and store a presigned URL for the given storage ID and operation.

        :param storage_id: Unique identifier for the file in the storage system.
        :param user_id: ID of the user requesting the presigned URL.
        :param operation_type: Type of operation (upload/download) for the presigned URL.
        :param filename: Name of the file associated with the presigned URL.
        :param expires_in: Time in seconds for which the presigned URL is valid.
        :return: Generated presigned URL as a string.
        """
        raise NotImplementedError
    
    async def get_presigned_url_from_token(self, token: str, raise_not_found: bool = True) -> PresignedURL | None:
        """
        Retrieve a presigned URL record from the database using its token.

        :param token: The unique token associated with the presigned URL.
        :param raise_not_found: Whether to raise NotFoundException if the token does not exist.
        :return: PresignedURL instance.
        """
        raise NotImplementedError
    
    async def delete_presigned_url(self, token: str) -> None:
        """
        Delete a presigned URL record from the database using its token.

        :param token: The unique token associated with the presigned URL.
        """
        raise NotImplementedError


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
    def file_storage_service(self, compression_service: CompressionService) -> FileStorageService:
        from ._storage import LocalFileStorageServiceImpl, MinioFileStorageServiceImpl
        if self.use_local:
            return LocalFileStorageServiceImpl(compression_service=compression_service, bucket="documents")
        return MinioFileStorageServiceImpl(compression_service=compression_service, bucket=settings.MINIO_BUCKET)

    @provide
    def artifact_file_storage_service(self) -> ArtifactFileStorageService:
        from ._storage import LocalFileStorageServiceImpl, MinioFileStorageServiceImpl
        if self.use_local:
            return LocalFileStorageServiceImpl(compression_service=None, bucket="artifacts")
        return MinioFileStorageServiceImpl(compression_service=None, bucket=settings.ARTIFACTS_MINIO_BUCKET)


class CompressionServiceProvider(Provider):
    """
    Provider for the CompressionService. Currently only Zstd is supported.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(scope=Scope.APP, *args, **kwargs)

    @provide
    def compression_service(self) -> CompressionService:
        from ._compression import CompressionServiceImpl
        return CompressionServiceImpl()
    

class PresignedURLServiceProvider(Provider):
    """
    Provider for presigned URL services.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(scope=Scope.REQUEST, *args, **kwargs)

    @provide
    def presigned_url_service(self, session: SessionType) -> PresignedURLService:
        from ._presigned_urls import PresignedURLServiceImpl
        return PresignedURLServiceImpl(session)
