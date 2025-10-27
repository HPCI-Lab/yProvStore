from dishka import Provider, Scope, provide

from models import DocumentRecord, DocumentGraphEntity, DocumentSubgraphDirection
from services.file_storage.service import FileStorageService
from ._prov_utils import ProvUtils


class GraphService:
    """
    Service for managing and querying provenance document graphs.
    This service provides methods to list or subgraph elements in a provenance document graph.
    """

    async def list_elements(
        self,
        document_record: DocumentRecord,
        entity_ids: list[str],
        entity_types: list[str]
    ) -> tuple[list[str], list[DocumentGraphEntity]]:
        """
        List elements in a provenance document graph filtering on entity IDs and types.
        The warnings list contains any issues encountered during the operation, such as invalid entity types.

        :param document_record: The document record referincing the graph.
        :param entity_ids: List of entity IDs to filter the results.
        :param entity_types: List of entity types to filter the results.
        :return: A tuple containing a list of warnings and a list of DocumentGraphEntity objects.
        """
        raise NotImplementedError

    async def subgraph(
        self,
        document_record: DocumentRecord,
        entity_ids: list[str],
        direction: DocumentSubgraphDirection = DocumentSubgraphDirection.BOTH
    ) -> tuple[list[str], dict]:
        """
        Get a subgraph of the document graph based on the specified entity IDs and direction.

        :param document_record: The document record referencing the graph.
        :param entity_ids: List of entity IDs to include in the subgraph.
        :param direction: The direction of the subgraph (forward, backward, or both).
        :return: A dictionary representing the subgraph elements.
        """
        raise NotImplementedError


class ProvDocumentGraphService(GraphService):
    """
    Implementation of the GraphService for managing provenance document graphs compliant with W3C PROV standards.
    """

    def __init__(self, file_storage_service: FileStorageService):
        self.file_storage_service = file_storage_service
        self.prov_utils = ProvUtils()

    async def list_elements(
        self,
        document_record: DocumentRecord,
        entity_ids: list[str],
        entity_types: list[str],
        is_element: bool | None = None,
        is_relation: bool | None = None
    ) -> tuple[list[str], list[DocumentGraphEntity]]:

        file_bytes = await self.file_storage_service.retrieve_file(document_record.storage_id)
        return await self.prov_utils.graph_list_elements(
            file_bytes=file_bytes,
            entity_ids=entity_ids,
            entity_types=entity_types,
            is_element=is_element,
            is_relation=is_relation
        )

    async def subgraph(
        self,
        document_record: DocumentRecord,
        entity_ids: list[str],
        direction: DocumentSubgraphDirection = DocumentSubgraphDirection.BOTH
    ) -> tuple[list[str], dict]:
        
        file_bytes = await self.file_storage_service.retrieve_file(document_record.storage_id)
        return await self.prov_utils.graph_subgraph(
            file_bytes=file_bytes,
            entity_ids=entity_ids,
            direction=direction
        )


class GraphServiceProvider(Provider):

    graph_service = provide(source=ProvDocumentGraphService, scope=Scope.APP, provides=GraphService)
