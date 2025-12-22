import logging
from datetime import datetime, timezone

from dishka import Provider, provide, Scope
from sqlalchemy.ext.asyncio import AsyncSession as SessionType

from application.exceptions.types import ConflictException, NotFoundException
from models import DocumentRecord
from services.db.sql.models import DBDocumentRecord
from services.db.sql.crud import SQLEntityDB

logger = logging.getLogger(__name__)


class DocumentRecordStorageService:
    """
    Interface for document records storage operations.
    """

    async def get_document_by_pid(self, pid: str, raise_not_found: bool = True) -> DocumentRecord | None:
        """
        Retrieve a document record by their pid.
        """
        raise NotImplementedError

    async def save_document(self, document_record: DocumentRecord) -> DocumentRecord:
        """
        Save a new document record to the storage.
        """
        raise NotImplementedError
    
    async def update_document(self, document_record: DocumentRecord) -> DocumentRecord:
        """
        Update an existing document record in the storage.
        """
        raise NotImplementedError
    
    async def document_is_updated(self, pid: str, updated_after: datetime) -> None:
        """
        Updates `updated_at` field of the document record.
        """
        raise NotImplementedError

    async def list_documents(self, page: int, page_size: int, updated_after: datetime | None = None,
                             created_after: datetime | None = None, pid: str | None = None) -> list[DocumentRecord]:
        """
        List all document records available in the storage.
        
        :param page: The page number for pagination (default is 0).
        :param page_size: The number of items per page (default is 10).
        :param updated_after: Optional timestamp to filter documents updated after a certain time.
        :param created_after: Optional timestamp to filter documents created after a certain time.
        :param pid: Optional PID to filter documents by their unique identifier.
        :return: A list of document records.
        """
        raise NotImplementedError
    
    async def delete_document(self, pid: str) -> None:
        """
        Delete a document record from the storage by its pid.
        """
        raise NotImplementedError


class DocumentRecordStorageServiceImpl(DocumentRecordStorageService, SQLEntityDB[DBDocumentRecord]):
    """
    Concrete implementation of DocumentRecordStorageService that interacts with a database.
    """

    def __init__(self, session: SessionType):
        super().__init__(session, model_type=DBDocumentRecord)

    async def get_document_by_pid(self, pid: str, raise_not_found: bool = True) -> DocumentRecord | None:
        db_document_record = await super()._get(pid, raise_not_found=raise_not_found)
        if not db_document_record:
            if raise_not_found:
                raise NotFoundException(f"Document with PID '{pid}' not found.")
            return None
        return db_document_record.to_document_record()

    async def save_document(self, document_record: DocumentRecord) -> DocumentRecord:
        if await super()._get(document_record.pid, raise_not_found=False):
            raise ConflictException(f"Document with PID '{document_record.pid}' already exists.")
        db_document_record = DBDocumentRecord.from_document_record(document_record)
        created_db_document_record = await super()._create(db_document_record)
        return created_db_document_record.to_document_record()
    
    async def document_is_updated(self, pid: str, updated_after: datetime) -> None:
        db_document_record = await super()._get(pid, raise_not_found=True)
        # Ensure updated_after is timezone-aware for comparison
        if updated_after.tzinfo is None:
            updated_after = updated_after.replace(tzinfo=timezone.utc)
        if db_document_record.updated_at < updated_after:
            db_document_record.updated_at = updated_after
            await super()._update(db_document_record)

    async def update_document(self, document_record: DocumentRecord) -> DocumentRecord:
        db_document_record = await super()._get(document_record.pid, raise_not_found=True)
        db_document_record.update_from_document_record(document_record)
        # Update the document record in the database
        new_record = await self._update(db_document_record)
        return new_record.to_document_record()

    async def list_documents(self, page: int, page_size: int, updated_after: datetime | None = None,
                             created_after: datetime | None = None, pid: str | None = None) -> list[DocumentRecord]:
        filters = {}
        if updated_after:
            filters['updated_at__ge'] = updated_after
        if created_after:
            filters['created_at__ge'] = created_after
        if pid:
            filters['id'] = pid
        db_documents = await super()._filter(page=page, page_size=page_size, **filters)
        return [db_document.to_document_record() for db_document in db_documents]
    
    async def delete_document(self, pid: str) -> None:
        await super().delete(pid, soft_delete=False)


class DocumentStorageProvider(Provider):

    document_record_storage_service = provide(source=DocumentRecordStorageServiceImpl, scope=Scope.REQUEST, provides=DocumentRecordStorageService)
