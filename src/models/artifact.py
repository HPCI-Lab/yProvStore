from dataclasses import dataclass
from datetime import datetime, timezone

from enum import Enum


@dataclass
class ArtifactRecord:
    pid: str
    storage_id: str
    owner_id: str
    filename: str
    created_at: str | None = None  # timestamp of creation
    updated_at: str | None = None  # timestamp of the last update
    hash: str | None = None  # optional hash 256 of the document content
    valid: bool = False  # indicates if the artifact is valid or has not been uploaded yet


class PresignedURLOperationType(Enum):
    UPLOAD = "upload"
    DOWNLOAD = "download"


@dataclass
class PresignedURL:
    token: str
    user_id: str
    storage_id: str
    filename: str
    operation_type: PresignedURLOperationType
    expires_at: str  # timestamp of expiration

    @property
    def artifact_pid(self) -> str:
        return self.storage_id

    def is_expired(self, current_timestamp: int = None) -> bool:
        if not current_timestamp:
            current_timestamp = int(datetime.now(tz=timezone.utc).timestamp())
        return current_timestamp >= int(self.expires_at)
