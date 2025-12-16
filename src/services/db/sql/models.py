from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Enum as SAEnum
from sqlalchemy.orm import relationship

from models.permission import DocumentPermission, PermissionLevel
from models.user import User
from models.document import DocumentRecord
from models.artifact import ArtifactRecord, PresignedURL, PresignedURLOperationType
from services.db.sql.base import BaseDBModel


class DBUser(BaseDBModel):
    """
    Database model for User.
    """
    __tablename__ = "users"

    id = Column(String(255), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    documents = relationship("DBDocumentRecord", back_populates="owner")
    artifacts = relationship("DBArtifactRecord", back_populates="owner")
    presigned_urls = relationship("DBPresignedURL", back_populates="user")
    permissions = relationship("DBDocumentPermission", back_populates="user")

    @classmethod
    def model_name(cls) -> str:
        """
        Return the name of the model.
        This is used for logging and response formatting.
        """
        return "User"

    @classmethod
    def from_user(cls, db_user: User) -> 'DBUser':
        """
        Convert a User instance to a DBUser instance.
        """
        return cls(id=db_user.id, email=db_user.email, password_hash=db_user.password_hash)

    def to_user(self) -> User:
        """
        Convert this DBUser instance to a User instance.
        """
        return User(id=self.id, email=self.email, password_hash=self.password_hash)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"

    def __str__(self):
        return self.email


class DBDocumentRecord(BaseDBModel):
    """
    Database model for DocumentRecord.
    """
    __tablename__ = "document_records"

    id = Column(String(255), primary_key=True, index=True)
    version = Column(Integer, nullable=False)
    storage_id = Column(String(255), nullable=False)
    owner_id = Column(String(255), ForeignKey('users.id'), nullable=False)
    parent_doc_pid = Column(String(255), nullable=True)
    hash = Column(String(64), nullable=True)  # SHA-256 hash
    lineage_id = Column(String(255), nullable=True)

    owner = relationship("DBUser", back_populates="documents")
    permissions = relationship("DBDocumentPermission", back_populates="document_record")

    @classmethod
    def model_name(cls) -> str:
        """
        Return the name of the model.
        This is used for logging and response formatting.
        """
        return "Provenance document record"

    def to_document_record(self) -> DocumentRecord:
        """
        Convert this DBDocumentRecord instance to a DocumentRecord instance.
        """
        return DocumentRecord(
            pid=self.id,
            version=self.version,
            storage_id=self.storage_id,
            owner_id=self.owner_id,
            parent_doc_pid=self.parent_doc_pid,
            lineage_id=self.lineage_id,
            hash=self.hash,
            created_at=self.created_at,
            updated_at=self.updated_at
        )
    
    def update_from_document_record(self, document_record: DocumentRecord) -> None:
        """
        Update this DBDocumentRecord instance from a DocumentRecord instance.
        """
        self.id = document_record.pid
        self.version = document_record.version
        self.storage_id = document_record.storage_id
        self.owner_id = document_record.owner_id
        self.parent_doc_pid = document_record.parent_doc_pid
        self.lineage_id = document_record.lineage_id
        self.hash = document_record.hash

    @classmethod
    def from_document_record(cls, document_record: DocumentRecord) -> 'DBDocumentRecord':
        """
        Convert a DocumentRecord instance to a DBDocumentRecord instance.
        """
        return cls(
            id=document_record.pid,
            version=document_record.version,
            storage_id=document_record.storage_id,
            owner_id=document_record.owner_id,
            parent_doc_pid=document_record.parent_doc_pid,
            hash=document_record.hash,
            lineage_id=document_record.lineage_id
        )


class DBDocumentPermission(BaseDBModel):
    """
    Database model for DocumentPermission.
    """
    __tablename__ = "document_permissions"

    id = Column(String(255), primary_key=True, index=True)
    pid = Column(String(255), ForeignKey('document_records.id'), nullable=False)
    user_id = Column(String(255), ForeignKey('users.id'), nullable=False)
    permission_level = Column(String(50), nullable=False)

    document_record = relationship("DBDocumentRecord", back_populates="permissions")
    user = relationship("DBUser", back_populates="permissions")

    @classmethod
    def model_name(cls) -> str:
        """
        Return the name of the model.
        This is used for logging and response formatting.
        """
        return "Document permission"

    @classmethod
    def from_document_permission(cls, permission: DocumentPermission) -> 'DBDocumentPermission':
        """
        Convert a DocumentPermission instance to a DBDocumentPermission instance.
        """
        return cls(
            pid=permission.pid,
            user_id=permission.user_id,
            permission_level=permission.permission_level.value
        )

    def to_document_permission(self) -> DocumentPermission:
        """
        Convert this DBDocumentPermission instance to a DocumentPermission instance.
        """
        return DocumentPermission(
            pid=self.pid,
            user_id=self.user_id,
            permission_level=PermissionLevel(self.permission_level)
        )


class DBArtifactRecord(BaseDBModel):
    """
    Database model for ArtifactRecord.
    """
    __tablename__ = "artifact_records"

    id = Column(String(255), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    storage_id = Column(String(255), nullable=False)
    owner_id = Column(String(255), ForeignKey('users.id'), nullable=False)
    hash = Column(String(64), nullable=True)  # SHA-256 hash
    valid = Column('valid', Boolean, default=False, nullable=False)

    owner = relationship("DBUser", back_populates="artifacts")

    @classmethod
    def model_name(cls) -> str:
        """
        Return the name of the model.
        This is used for logging and response formatting.
        """
        return "Artifact record"

    def to_artifact_record(self) -> ArtifactRecord:
        """
        Convert this DBArtifactRecord instance to a ArtifactRecord instance.
        """
        return ArtifactRecord(
            pid=self.id,
            filename=self.filename,
            storage_id=self.storage_id,
            owner_id=self.owner_id,
            hash=self.hash,
            created_at=self.created_at,
            updated_at=self.updated_at,
            valid=self.valid
        )

    def update_from_artifact_record(self, artifact_record: ArtifactRecord) -> None:
        """
        Update this DBArtifactRecord instance from a ArtifactRecord instance.
        """
        self.id = artifact_record.pid
        self.filename = artifact_record.filename
        self.storage_id = artifact_record.storage_id
        self.owner_id = artifact_record.owner_id
        self.hash = artifact_record.hash
        self.valid = artifact_record.valid

    @classmethod
    def from_artifact_record(cls, artifact_record: ArtifactRecord) -> 'DBArtifactRecord':
        """
        Convert a ArtifactRecord instance to a DBArtifactRecord instance.
        """
        return cls(
            id=artifact_record.pid,
            filename=artifact_record.filename,
            storage_id=artifact_record.storage_id,
            owner_id=artifact_record.owner_id,
            hash=artifact_record.hash,
            valid=artifact_record.valid
        )


class DBPresignedURL(BaseDBModel):
    """
    Database model for PresignedURL.
    """
    __tablename__ = "presigned_urls"

    id = Column(String(255), primary_key=True, index=True)
    user_id = Column(String(255), ForeignKey('users.id'), nullable=False)
    storage_id = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    operation_type = Column(SAEnum(PresignedURLOperationType), nullable=False)
    expires_at = Column(Integer, nullable=False)  # Unix timestamp

    user = relationship("DBUser", back_populates="presigned_urls")

    @classmethod
    def model_name(cls) -> str:
        """
        Return the name of the model.
        This is used for logging and response formatting.
        """
        return "Presigned URL"
    
    @classmethod
    def from_presigned_url(cls, presigned_url: PresignedURL, user_id: str) -> 'DBPresignedURL':
        """
        Convert a PresignedURL instance to a DBPresignedURL instance.
        """
        return cls(
            id=presigned_url.token,
            user_id=user_id,
            storage_id=presigned_url.storage_id,
            filename=presigned_url.filename,
            operation_type=presigned_url.operation_type,
            expires_at=int(presigned_url.expires_at.timestamp())
        )
    
    def to_presigned_url(self) -> PresignedURL:
        """
        Convert this DBPresignedURL instance to a PresignedURL instance.
        """
        return PresignedURL(
            token=self.id,
            user_id=self.user_id,
            storage_id=self.storage_id,
            filename=self.filename,
            expires_at=self.expires_at,
            operation_type=self.operation_type
        )
