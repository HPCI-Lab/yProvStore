from dishka import Provider, provide, Scope
from sqlalchemy.orm import Session as SessionType

from application.exceptions.types import ConflictException, ForbiddenException, IntegrityException
from models import DocumentPermission, User, DocumentRecord, PermissionLevel, PidRecord
from services.document_storage.service import DocumentRecordStorageService
from services.db.sql.models import DBDocumentPermission
from services.pid.service import PidService
from services.db.sql.crud import SQLEntityDB


class DocumentPermissionStorageService:
    """
    Service for managing document permissions.
    """
    document_record_storage: DocumentRecordStorageService
    pid_service: PidService

    async def list_permissions_for_doc(self, pid: str) -> list[DocumentPermission]:
        """
        List all permissions for a specific document.
        """
        raise NotImplementedError

    async def list_permissions_for_doc_and_user(self, pid: str, user_id: str) -> list[DocumentPermission]:
        """
        List permissions for a specific document and user.
        """
        raise NotImplementedError

    async def save_permission(self, permission: DocumentPermission) -> DocumentPermission:
        """
        Save a new permission for a document.
        """
        raise NotImplementedError

    async def validate_user_permission(self, user: User, doc: DocumentRecord, permission_level: PermissionLevel) -> None:
        """
        Check if a user has a specific permission level for a document.
        """
        raise NotImplementedError
    
    async def get_first_document_record(self, doc: DocumentRecord) -> DocumentRecord:
        """
        Get the first version document record based on the PID lineage.
        """
        if not self.document_record_storage or not self.pid_service:
            raise Exception("DocumentRecordStorageService and PidService must be set before calling this method.")
        if doc.version != 1:
            # Fetch the first version of the document
            if not doc.parent_doc_pid:
                raise IntegrityException("Document is not a first version but has no parent PID.")
            parent_document_pid_record: PidRecord = await self.pid_service.get_pid_record(doc.parent_doc_pid, raise_not_found=False)
            if not parent_document_pid_record:
                raise IntegrityException(f"Parent document record with PID '{doc.parent_doc_pid}' not found.")
            if parent_document_pid_record.version == 1:
                first_document_pid = parent_document_pid_record.pid
            else:
                if not parent_document_pid_record.tree_pid:
                    raise IntegrityException(f"Parent document record with PID '{doc.parent_doc_pid}' has no tree PID and its version is not 1.")
                tree_pid_record: PidRecord = await self.pid_service.get_pid_record(parent_document_pid_record.tree_pid, raise_not_found=False)
                if not tree_pid_record:
                    raise IntegrityException(f"Tree PID record with PID '{parent_document_pid_record.tree_pid}' not found.")
                if not tree_pid_record.first_document_pid:
                    raise IntegrityException(f"Tree PID record with PID '{parent_document_pid_record.tree_pid}' has no first document PID.")
                first_document_pid = tree_pid_record.first_document_pid
            first_document: DocumentRecord = await self.document_record_storage.get_document_by_pid(first_document_pid, raise_not_found=False)
        else:
            first_document = doc
        if not first_document:
            raise ForbiddenException(f"First version document with PID '{tree_pid_record.first_document_pid}' not found in this server instance, cannot validate permissions.")
        return first_document


class DocumentPermissionStorageServiceImpl(DocumentPermissionStorageService, SQLEntityDB[DBDocumentPermission]):
    """
    Concrete implementation of DocumentPermissionStorageService that interacts with a database.
    """

    def __init__(self, session: SessionType, pid_service: PidService, document_record_storage: DocumentRecordStorageService):
        super().__init__(session, model_type=DBDocumentPermission)
        self.pid_service = pid_service
        self.document_record_storage = document_record_storage

    async def list_permissions_for_doc(self, pid: str) -> list[DocumentPermission]:
        db_permissions = await super()._filter(pid=pid)
        return [db_permission.to_document_permission() for db_permission in db_permissions]

    async def list_permissions_for_doc_and_user(self, pid: str, user_id: str) -> list[DocumentPermission]:
        db_permissions = await super()._filter(pid=pid, user_id=user_id)
        return [db_permission.to_document_permission() for db_permission in db_permissions]

    async def save_permission(self, permission: DocumentPermission) -> DocumentPermission:
        existing_permissions = await super()._filter(pid=permission.pid, user_id=permission.user_id)
        if len(existing_permissions) > 0:
            raise ConflictException(f"Permission for user '{permission.user_id}' on document '{permission.pid}' already exists.")
        db_permission = DBDocumentPermission.from_document_permission(permission)
        created_db_permission = await super()._create(db_permission)
        return created_db_permission.to_document_permission()

    async def validate_user_permission(self, user: User, doc: DocumentRecord, permission_level: PermissionLevel) -> None:
        """
        Validate if a user has the required permission level on a document.
        To maintain consistency, this method checks the first version of the document in its lineage.
        To create a new version, a user must have WRITE permissions on the first version of the document.
        Additionally, the first version document record must be present in this server instance.
        """
        if not user or not doc:
            raise ValueError("User and document must be provided to check permissions.")
        
        first_document = await self.get_first_document_record(doc)
        
        # Validate if the user has the required permission level on the first version document
        if first_document.owner_id == user.id:
            return
        db_permission = await super()._filter(pid=first_document.pid, user_id=user.id)
        if len(db_permission) > 1:
            raise ConflictException(f"Multiple permissions found for user '{user.email}' on document '{first_document.pid}'.")
        elif len(db_permission) == 1:
            if PermissionLevel(db_permission[0].permission_level) >= permission_level:
                return True
        raise ForbiddenException(
            f"User '{user.email}' does not have {permission_level} permissions for document '{first_document.pid}'."
        )


class PermissionStorageProvider(Provider):
    permission_storage_service = provide(
        source=DocumentPermissionStorageServiceImpl,
        scope=Scope.REQUEST,
        provides=DocumentPermissionStorageService
    )
