import logging
from datetime import datetime

from dishka import Provider, provide, Scope
from sqlalchemy.ext.asyncio import AsyncSession as SessionType

from application.exceptions.types import ConflictException, NotFoundException
from models import ArtifactRecord
from services.db.sql.models import DBArtifactRecord
from services.db.sql.crud import SQLEntityDB

logger = logging.getLogger(__name__)


class ArtifactRecordStorageService:
    """
    Interface for artifact records storage operations.
    """

    async def get_artifact_by_pid(self, pid: str, raise_not_found: bool = True) -> ArtifactRecord | None:
        """
        Retrieve a artifact record by their pid.
        """
        raise NotImplementedError

    async def save_artifact(self, artifact_record: ArtifactRecord) -> ArtifactRecord:
        """
        Save a new artifact record to the storage.
        """
        raise NotImplementedError
    
    async def update_artifact(self, artifact_record: ArtifactRecord) -> ArtifactRecord:
        """
        Update an existing artifact record in the storage.
        """
        raise NotImplementedError

    async def list_artifacts(self, page: int, page_size: int, updated_after: datetime | None = None,
                             created_after: datetime | None = None, pid: str | None = None) -> list[ArtifactRecord]:
        """
        List all artifact records available in the storage.
        
        :param page: The page number for pagination (default is 0).
        :param page_size: The number of items per page (default is 10).
        :param updated_after: Optional timestamp to filter artifacts updated after a certain time.
        :param created_after: Optional timestamp to filter artifacts created after a certain time.
        :param pid: Optional PID to filter artifacts by their unique identifier.
        :return: A list of artifact records.
        """
        raise NotImplementedError

    async def delete_artifact(self, pid: str) -> None:
        """
        Delete a artifact record from the storage by its pid.
        """
        raise NotImplementedError


class ArtifactRecordStorageServiceImpl(ArtifactRecordStorageService, SQLEntityDB[DBArtifactRecord]):
    """
    Concrete implementation of ArtifactRecordStorageService that interacts with a database.
    """

    def __init__(self, session: SessionType):
        super().__init__(session, model_type=DBArtifactRecord)

    async def get_artifact_by_pid(self, pid: str, raise_not_found: bool = True) -> ArtifactRecord | None:
        db_artifact_record = await super()._get(pid, raise_not_found=raise_not_found)
        if not db_artifact_record:
            if raise_not_found:
                raise NotFoundException(f"Artifact with PID '{pid}' not found.")
            return None
        return db_artifact_record.to_artifact_record()

    async def save_artifact(self, artifact_record: ArtifactRecord) -> ArtifactRecord:
        if await super()._get(artifact_record.pid, raise_not_found=False):
            raise ConflictException(f"Artifact with PID '{artifact_record.pid}' already exists.")
        db_artifact_record = DBArtifactRecord.from_artifact_record(artifact_record)
        created_db_artifact_record = await super()._create(db_artifact_record)
        return created_db_artifact_record.to_artifact_record()
    
    async def update_artifact(self, artifact_record: ArtifactRecord) -> ArtifactRecord:
        db_artifact_record = await super()._get(artifact_record.pid, raise_not_found=True)
        db_artifact_record.update_from_artifact_record(artifact_record)
        updated_db_artifact_record = await super()._update(db_artifact_record)
        return updated_db_artifact_record.to_artifact_record()

    async def list_artifacts(self, page: int, page_size: int, updated_after: datetime | None = None,
                             created_after: datetime | None = None, pid: str | None = None) -> list[ArtifactRecord]:
        filters = {}
        if updated_after:
            filters['updated_at__ge'] = updated_after
        if created_after:
            filters['created_at__ge'] = created_after
        if pid:
            filters['pid'] = pid
        db_artifacts = await super()._filter(page=page, page_size=page_size, **filters)
        return [db_artifact.to_artifact_record() for db_artifact in db_artifacts]

    async def delete_artifact(self, pid: str) -> None:
        await super().delete(pid, soft_delete=False)


class ArtifactStorageProvider(Provider):

    artifact_record_storage_service = provide(source=ArtifactRecordStorageServiceImpl, scope=Scope.REQUEST, provides=ArtifactRecordStorageService)
