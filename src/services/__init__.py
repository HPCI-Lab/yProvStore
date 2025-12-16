from dishka.integrations.fastapi import FastapiProvider

from .auth.service import AuthServiceProvider
from .db.service import DBServiceProvider
from .user_storage.service import UserStorageProvider
from .document_storage.service import DocumentStorageProvider
from .pid.service import PidServiceProvider
from .file_storage.service import FileStorageServiceProvider, CompressionServiceProvider, PresignedURLServiceProvider
from .permission_storage.service import PermissionStorageProvider
from .metadata.service import DocumentMetadataServiceProvider
from .graph.service import GraphServiceProvider
from .artifact_storage.service import ArtifactStorageProvider


__all__ = ("providers",)


providers = [
    AuthServiceProvider,
    DBServiceProvider,
    UserStorageProvider,
    FastapiProvider,
    DocumentStorageProvider,
    PidServiceProvider,
    CompressionServiceProvider,
    FileStorageServiceProvider,
    PermissionStorageProvider,
    DocumentMetadataServiceProvider,
    GraphServiceProvider,
    ArtifactStorageProvider,
    PresignedURLServiceProvider
]
