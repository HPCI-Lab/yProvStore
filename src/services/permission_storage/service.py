from dishka import Provider, provide, Scope
from sqlalchemy.orm import Session as SessionType

from application.exceptions.types import ConflictException, ForbiddenException
from models import DocumentPermission, User, DocumentRecord, PermissionLevel
from services.db.sql.models import DBDocumentPermission
from services.db.sql.crud import SQLEntityDB


class DocumentPermissionStorageService:
    """
    Service for managing document permissions.
    """

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


class DocumentPermissionStorageServiceImpl(DocumentPermissionStorageService, SQLEntityDB[DBDocumentPermission]):
    """
    Concrete implementation of DocumentPermissionStorageService that interacts with a database.
    """

    def __init__(self, session: SessionType, ):
        super().__init__(session, model_type=DBDocumentPermission)

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
        if not user or not doc:
            raise ValueError("User and document must be provided to check permissions.")
        if doc.owner_id == user.id:
            return
        db_permission = await super()._filter(pid=doc.pid, user_id=user.id)
        if len(db_permission) > 1:
            raise ConflictException(f"Multiple permissions found for user '{user.email}' on document '{doc.pid}'.")
        elif len(db_permission) == 1:
            if PermissionLevel(db_permission[0].permission_level) >= permission_level:
                return True
        raise ForbiddenException(
            f"User '{user.email}' does not have {permission_level} permissions for document '{doc.pid}'."
        )


class PermissionStorageProvider(Provider):
    permission_storage_service = provide(
        source=DocumentPermissionStorageServiceImpl,
        scope=Scope.REQUEST,
        provides=DocumentPermissionStorageService
    )
