import logging

from dishka import Provider, provide, Scope

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


# TODO: implement correct file storage service integration


class FileStorageServiceProvider(Provider):
    """
    Provider for the FileStorageService.
    """

    file_storage_service = provide(source=LocalFileStorageServiceImpl, scope=Scope.APP, provides=FileStorageService)
