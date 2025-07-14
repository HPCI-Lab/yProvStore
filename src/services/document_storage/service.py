from dishka import Provider, provide, Scope
from sqlalchemy.orm import Session as SessionType

from application.exceptions.types import ConflictException
from models import DocumentRecord
from services.db.sql.models import DBDocumentRecord
from services.db.sql.crud import SQLEntityDB


class DocumentRecordStorageService:
    """
    Interface for document records storage operations.
    """

    async def get_document_by_pid(self, pid: str) -> DocumentRecord:
        """
        Retrieve a document record by their pid.
        """
        raise NotImplementedError

    async def save_document(self, document: DocumentRecord) -> DocumentRecord:
        """
        Save a new document record to the storage.
        """
        raise NotImplementedError

    async def list_documents(self) -> list[DocumentRecord]:
        """
        List all document records available in the storage.
        """
        raise NotImplementedError


class DocumentRecordStorageServiceImpl(DocumentRecordStorageService, SQLEntityDB[DBDocumentRecord]):
    """
    Concrete implementation of DocumentRecordStorageService that interacts with a database.
    """

    def __init__(self, session: SessionType):
        super().__init__(session, model_type=DBDocumentRecord)

    async def get_document_by_pid(self, pid: str) -> DocumentRecord:
        db_document_record = await super()._get(pid)
        return db_document_record.to_document_record()

    async def save_document(self, document_record: DocumentRecord) -> DocumentRecord:
        if await super()._get(document_record.pid, raise_not_found=False):
            raise ConflictException(f"Document with PID '{document_record.pid}' already exists.")
        db_document_record = DBDocumentRecord.from_document_record(document_record)
        created_db_document_record = await super()._create(db_document_record)
        return created_db_document_record.to_document_record()

    async def list_documents(self) -> list[DocumentRecord]:
        db_documents = await super()._filter()
        return [db_document.to_document_record() for db_document in db_documents]


class DocumentStorageProvider(Provider):

    document_record_storage_service = provide(source=DocumentRecordStorageServiceImpl, scope=Scope.REQUEST, provides=DocumentRecordStorageService)
