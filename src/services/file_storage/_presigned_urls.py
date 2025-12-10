from datetime import datetime, timezone

from application.exceptions.types import NotFoundException
from models import PresignedURL, PresignedURLOperationType
from services.db.sql.models import DBPresignedURL
from services.db.sql.crud import SQLEntityDB
from services.file_storage.service import PresignedURLService


class PresignedURLServiceImpl(PresignedURLService, SQLEntityDB[DBPresignedURL]):
    
    async def generate_presigned_url(self, user_id: str, storage_id: str, operation_type: PresignedURLOperationType, filename: str, expires_in: int = 3600) -> PresignedURL:
        """
        Generate a new presigned URL for downloading a file from storage.
        """
        current_unix_timestamp = int(datetime.now(timezone.utc).timestamp())

        expires_at = current_unix_timestamp + expires_in

        presigned_url: DBPresignedURL = await super()._create(
            user_id=user_id,
            storage_id=storage_id,
            filename=filename,
            expires_at=expires_at
        )

        return presigned_url.to_presigned_url()
    
    async def get_presigned_url_from_token(self, token: str, raise_not_found: bool = True) -> PresignedURL | None:
        """
        Retrieve a presigned URL record from the database using its token.
        """
        db_presigned_url = await super()._get(token, raise_not_found=raise_not_found)
        if not db_presigned_url:
            if raise_not_found:
                raise NotFoundException(f"Presigned URL with token '{token}' not found.")
            return None
        return db_presigned_url.to_presigned_url()
    
    async def delete_presigned_url(self, token: str) -> None:
        """
        Delete a presigned URL record from the database using its token.
        """
        await super().delete(token, soft_delete=False)
