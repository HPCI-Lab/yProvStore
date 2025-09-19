from dishka import provide, Scope, Provider

from models import DocumentMetadata
from services.pid.service import PidService


class DocumentMetadataService:
    """
    Service for managing document metadata.
    """
    async def get_document_metadata(self, pid: str) -> DocumentMetadata:
        """
        Retrieves metadata for a specific document by its PID.
        
        :param pid: The unique identifier of the document.
        :return: DocumentMetadata object.
        """
        raise NotImplementedError
    
    async def update_document_metadata(self, pid: str, metadata: DocumentMetadata) -> DocumentMetadata:
        """
        Updates metadata for a specific document by its PID.
        
        :param pid: The unique identifier of the document.
        :param metadata: DocumentMetadata object containing updated metadata.
        :return: Updated DocumentMetadata object.
        """
        raise NotImplementedError
    

class PIDRecordDocumentMetadataService(DocumentMetadataService):
    """
    Service for managing document metadata using PID records.
    """
    def __init__(self, pid_service: PidService):
        super().__init__()
        self.pid_service = pid_service

    async def get_document_metadata(self, pid: str) -> DocumentMetadata:
        # Fetch the PID record
        pid_record = await self.pid_service.get_pid_record(pid)

        return DocumentMetadata.from_dict(pid_record.other)
    
    async def update_document_metadata(self, pid: str, metadata: DocumentMetadata) -> DocumentMetadata:
        # Fetch the PID record
        pid_record = await self.pid_service.get_pid_record(pid)

        # Update the metadata in the PID record
        pid_record.other = metadata.to_dict()
        
        # Save the updated PID record
        pid_record = await self.pid_service.update_pid_record(pid_record)

        return DocumentMetadata.from_dict(pid_record.other)


class DocumentMetadataServiceProvider(Provider):
    
    document_metadata_service = provide(source=PIDRecordDocumentMetadataService, scope=Scope.APP, provides=DocumentMetadataService)
