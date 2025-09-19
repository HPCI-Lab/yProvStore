import io
import importlib
import logging
from typing import Optional

from dishka import Provider, provide, Scope

from application import settings
from application.settings import TMP_PATH
from application.exceptions.types import ConflictException, NotFoundException, ServiceUnavailableException

logger = logging.getLogger(__name__)


class FileStorageService:

    async def store_file(self, storage_id: str, file_data: bytes) -> None:
        """
        Store a file in the storage system.

        :param storage_id: Unique identifier for the file in the storage system.
        :param file_data: The binary data of the file to be stored.
        """
        raise NotImplementedError

    async def retrieve_file(self, storage_id: str) -> bytes:
        """
        Retrieve a file from the storage system.

        :param storage_id: Unique identifier for the file in the storage system.
        """
        raise NotImplementedError


class LocalFileStorageServiceImpl(FileStorageService):
    """
    Local file storage implementation for testing purposes.
    """

    # TODO: manage compression

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
            with open(file_path, 'wb') as f:
                f.write(file_data)
        except Exception as e:
            logger.error(f"Error storing file {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to store file.")

    async def retrieve_file(self, storage_id: str) -> bytes:
        file_path = self.documents_path / storage_id
        if not file_path.exists():
            raise NotFoundException(f"File with ID '{storage_id}' not found.")

        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error retrieving file {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to retrieve file.")


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
                # If not found, proceed to upload; other S3 errors -> service issue
                if getattr(e, "code", "") not in ("NoSuchKey", "NoSuchObject", "NotFound"):
                    logger.error(f"MinIO stat_object error for {storage_id}: {e}")
                    raise ServiceUnavailableException("Failed to access storage.")
            else:
                # Unexpected error; log and proceed to attempt upload
                logger.warning(f"Unexpected error during stat_object for {storage_id}: {e}. Proceeding to upload.")

        try:
            data_stream = io.BytesIO(file_data)
            self.client.put_object(
                self.bucket,
                storage_id,
                data=data_stream,
                length=len(file_data),
                content_type="application/octet-stream",
            )
        except Exception as e:
            if isinstance(e, getattr(self, "_S3Error", tuple())):
                logger.error(f"MinIO put_object error for {storage_id}: {e}")
                raise ServiceUnavailableException("Failed to store file.")
            logger.error(f"Unexpected error storing file {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to store file.")

    async def retrieve_file(self, storage_id: str) -> bytes:
        try:
            response = self.client.get_object(self.bucket, storage_id)
            try:
                data = response.read()
                return data
            finally:
                response.close()
                response.release_conn()
        except Exception as e:
            if isinstance(e, getattr(self, "_S3Error", tuple())):
                # Map not found
                if getattr(e, "code", "") in ("NoSuchKey", "NoSuchObject", "NotFound"):
                    raise NotFoundException(f"File with ID '{storage_id}' not found.")
                logger.error(f"MinIO get_object error for {storage_id}: {e}")
                raise ServiceUnavailableException("Failed to retrieve file.")
            logger.error(f"Unexpected error retrieving file {storage_id}: {e}")
            raise ServiceUnavailableException("Failed to retrieve file.")


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
