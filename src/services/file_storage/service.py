import logging
from enum import Enum
from typing import AsyncIterator

from fastapi import UploadFile
from dishka import Provider, provide, Scope

from application import settings


logger = logging.getLogger(__name__)


class CompressionStandard(Enum):
    ZSTD = "zstd"


class DocumentNotCompressedException(Exception):
    """Raised when a document is expected to be compressed but is not."""
    pass


class FileStorageService:

    async def store_file(self, storage_id: str, file_data: bytes, skip_compression: bool = False, ignore_compression: bool = False) -> str:
        """
        Store a file in the storage system.
        Already reads all data into memory, so not suitable for large files.

        :param storage_id: Unique identifier for the file in the storage system.
        :param file_data: The binary data of the file to be stored.
        :param skip_compression: If True, store without compressing the file. If enabled, the document
                                 will be still be uncompressed on-the-fly just to compute the hash.
                                 Therefore, the document must be compressed according to the supported compression standard.
        :param ignore_compression: If True, ignore compression mechanism entirely and store as-is.
        :return: The SHA-256 hash of the stored file as a hex string.
        """
        raise NotImplementedError

    async def store_file_from_uploadfile(self, storage_id: str, upload_file: UploadFile, skip_compression: bool = False, ignore_compression: bool = False) -> str:
        """
        Stream the UploadFile (async) to a temp file while computing SHA-256, then persist it.
        More memory efficient for large files than reading all into memory first (store_file).

        :param storage_id: Unique identifier for the file in the storage system.
        :param upload_file: The UploadFile instance from FastAPI.
        :param skip_compression: If True, store without compressing the file. If enabled, the document 
                                 will be still be uncompressed on-the-fly just to compute the hash.
                                 Therefore, the document must be compressed according to the supported compression standard.
        :param ignore_compression: If True, ignore compression mechanism entirely and store as-is.
        :return: The SHA-256 hash of the stored file as a hex string.
        """
        raise NotImplementedError

    async def retrieve_file(self, storage_id: str, skip_decompression: bool = False, ignore_compression: bool = False) -> AsyncIterator[bytes]:
        """
        Retrieve a file from the storage system as an async iterator of decompressed chunks.

        :param storage_id: Unique identifier for the file in the storage system.
        :param skip_decompression: If True, stream without decompressing the file.
        :param ignore_compression: If True, ignore compression mechanism entirely and retrieve as-is.
        :raise DocumentNotCompressedException: If skip_decompression is True but the document is not compressed.
        :return: Async iterator yielding decompressed bytes chunks.
        """
        raise NotImplementedError
    
    async def delete_file(self, storage_id: str) -> None:
        """
        Delete a file from the storage system.

        :param storage_id: Unique identifier for the file in the storage system.
        """
        raise NotImplementedError
    
    @staticmethod
    def get_compression_standard() -> CompressionStandard:
        """
        Get the default compression standard used by the service.

        :return: CompressionStandard enum value.
        """
        return CompressionStandard.ZSTD
    

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
            return LocalFileStorageServiceImpl(compression_service=compression_service)
        return MinioFileStorageServiceImpl(compression_service=compression_service)


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
