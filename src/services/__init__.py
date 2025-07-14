from dishka.integrations.fastapi import FastapiProvider

from services.auth.service import AuthServiceProvider
from services.db.service import DBServiceProvider
from services.user_storage.service import UserStorageProvider
from services.document_storage.service import DocumentStorageProvider
from services.pid.service import PidServiceProvider
from services.file_storage.service import FileStorageServiceProvider
from services.permission_storage.service import PermissionStorageProvider


__all__ = ("providers",)


providers = [
    AuthServiceProvider,
    DBServiceProvider,
    UserStorageProvider,
    FastapiProvider,
    DocumentStorageProvider,
    PidServiceProvider,
    FileStorageServiceProvider,
    PermissionStorageProvider
]
