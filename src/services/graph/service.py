from prov.model import ProvDocument, PROV_N_MAP, ADDITIONAL_N_MAP
from dishka import Provider, Scope, provide

from models import DocumentRecord, DocumentGraphEntity, DocumentSubgraphDirection
from services.file_storage.service import FileStorageService


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
        raise NotImplemented
    
    async def subgraph(
        self,
        document_record: DocumentRecord,
        entity_ids: list[str],
        direction: DocumentSubgraphDirection = DocumentSubgraphDirection.BOTH
    ) -> list[DocumentGraphEntity]:
        """
        Get a subgraph of the document graph based on the specified entity IDs and direction.

        :param document_record: The document record referencing the graph.
        :param entity_ids: List of entity IDs to include in the subgraph.
        :param direction: The direction of the subgraph (forward, backward, or both).
        :return: A list of DocumentGraphEntity objects representing the subgraph elements.
        """
        raise NotImplemented
    

class ProvDocumentGraphService(GraphService):
    """
    Implementation of the GraphService for managing provenance document graphs compliant with W3C PROV standards.
    """

    def __init__(self, file_storage_service: FileStorageService):
        self.file_storage_service = file_storage_service
        self.mapping = PROV_N_MAP | ADDITIONAL_N_MAP
        self.mapping_values = set(self.mapping.values())

    async def list_elements(
        self,
        document_record: DocumentRecord,
        entity_ids: list[str],
        entity_types: list[str]
    ) -> tuple[list[str], list[DocumentGraphEntity]]:
        
        # TODO: improve efficiency?

        warnings = []

        file_bytes = await self.file_storage_service.retrieve_file(document_record.storage_id)

        try:
            prov_doc = ProvDocument.deserialize(content=file_bytes)
        except Exception as e:
            warnings.append(f"Document {document_record.pid} is not a valid PROV document")
            # TODO: manage in rdf?
            return warnings, []

        if entity_ids is None:
            entity_ids = []
        if entity_types is None:
            entity_types = []

        # Validate all entity types are available in the PROV terms
        set_types = set(entity_types)
        for set_type in set_types:
            if not set_type in self.mapping_values:
                warnings.append(f"Entity type '{set_type}' is not a valid PROV type.")

        prov_records = prov_doc.flattened().get_records()
        if entity_types:
            prov_records = [r for r in prov_records if self.mapping.get(r.get_type(), "Unknown") in entity_types]
        if entity_ids:
            prov_records = [r for r in prov_records if str(r.identifier) in entity_ids]
        return warnings, [
            DocumentGraphEntity(
                id=str(record.identifier) if record.identifier else "",
                type=str(self.mapping.get(record.get_type(), "Unknown")),
                group=str(record.get_type()),
                is_element=record.is_element(),
                is_relation=record.is_relation(),
                data={str(a[0]): str(a[1]) for a in record.attributes}
            )
            for record in prov_records
        ]

    async def subgraph(
        self,
        document_record: DocumentRecord,
        entity_ids: list[str],
        direction: DocumentSubgraphDirection = DocumentSubgraphDirection.BOTH
    ) -> list[DocumentGraphEntity]:
        # Implementation logic to fetch subgraph from the document graph
        raise NotImplementedError


class GraphServiceProvider(Provider):

    graph_service = provide(source=ProvDocumentGraphService, scope=Scope.APP, provides=GraphService)
