import json
from typing import TypedDict

from prov.model import ProvDocument, ProvRelation, ProvElement, ProvRecord, PROV_N_MAP, ADDITIONAL_N_MAP
from prov.graph import INFERRED_ELEMENT_CLASS

from models import DocumentGraphEntity, DocumentSubgraphDirection


class DirectedRelation(TypedDict):
    """
    Represents a directed relation in the graph.
    """
    source: str
    target: str
    relation: ProvRelation

    def __init__(self, source: str, target: str, relation: ProvRelation):
        self.source = source
        self.target = target
        self.relation = relation

    @staticmethod
    def get_directed_nodes(relation: ProvRelation) -> tuple[str, str]:

        # TODO: handle more complex cases

        attr_pair_1, attr_pair_2 = relation.formal_attributes[:2]
        # only need the QualifiedName (i.e. the value of the attribute)
        return str(attr_pair_1[1]), str(attr_pair_2[1])


class ProvUtils:
    def __init__(self):
        self.mapping = PROV_N_MAP | ADDITIONAL_N_MAP
        self.mapping_values = set(self.mapping.values())

    async def graph_list_elements(
        self,
        file_bytes: bytes,
        entity_ids: list[str],
        entity_types: list[str],
        is_element: bool | None = None,
        is_relation: bool | None = None
    ) -> tuple[list[str], list[DocumentGraphEntity]]:
        """
        List elements in a provenance document graph.

        :param file_bytes: The bytes of the PROV document.
        :param entity_ids: List of entity IDs to filter the results.
        :param entity_types: List of entity types to filter the results.
        :param is_element: Filter by whether the entity is an element.
        :param is_relation: Filter by whether the entity is a relation.
        :return: A tuple containing a list of warnings and a list of DocumentGraphEntity objects
        """

        # TODO: improve efficiency?

        warnings = []

        try:
            prov_doc = ProvDocument.deserialize(content=file_bytes)
        except Exception:
            warnings.append("The document is not a valid PROV document")
            # TODO: manage in rdf?
            return warnings, []

        if entity_ids is None:
            entity_ids = []
        if entity_types is None:
            entity_types = []

        # Validate all entity types are available in the PROV terms
        set_types = set(entity_types)
        for set_type in set_types:
            if set_type not in self.mapping_values:
                warnings.append(f"Entity type '{set_type}' is not a valid PROV type.")

        prov_records = prov_doc.unified().flattened().get_records()
        if entity_types:
            prov_records = [r for r in prov_records if self.mapping.get(r.get_type(), "Unknown") in entity_types]
        if entity_ids:
            prov_records = [r for r in prov_records if str(r.identifier) in entity_ids]
        if is_element is not None:
            prov_records = [r for r in prov_records if r.is_element() == is_element]
        if is_relation is not None:
            prov_records = [r for r in prov_records if r.is_relation() == is_relation]
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
    
    async def graph_subgraph(
        self,
        file_bytes: bytes,
        entity_ids: list[str],
        direction: DocumentSubgraphDirection = DocumentSubgraphDirection.BOTH
    ) -> tuple[list[str], dict]:
        """
        Get a subgraph of the document graph based on the specified entity IDs and direction.

        :param file_bytes: The bytes of the PROV document.
        :param entity_ids: List of entity IDs to include in the subgraph.
        :return: A tuple containing a list of warnings and a dictionary representing the subgraph in PROV-JSON format.
        """ 

        warnings = []
        if not entity_ids:
            warnings.append("No entity IDs provided for subgraph extraction.")
            return warnings, {}
        
        try:
            prov_doc = ProvDocument.deserialize(content=file_bytes)
        except Exception:
            # TODO: manage in rdf?
            warnings.append("The document is not a valid PROV document.")
            return warnings, {}

        new_doc = ProvDocument()
        unified = prov_doc.unified()
        node_map: dict[str, ProvElement] = dict()
        records_to_include: set[ProvRecord] = set()
        for element in unified.get_records(ProvElement):
            node_map[str(element.identifier)] = element
            if str(element.identifier) in entity_ids:
                records_to_include.add(element)

        if not records_to_include:
            warnings.append(f"No records found for the provided entity IDs: {entity_ids}.")
            return warnings, {}

        node_relations: dict[str, list[DirectedRelation]] = {}

        # Code readapted from `prov.graph.prov_to_graph`
        for relation in unified.get_records(ProvRelation):
            # taking the first two elements of a relation
            attr_pair_1, attr_pair_2 = relation.formal_attributes[:2]
            
            qn1, qn2 = DirectedRelation.get_directed_nodes(relation)
            
            if qn1 and qn2:  # only proceed if both ends of the relation exist
                try:
                    if qn1 not in node_map:
                        node_map[qn1] = INFERRED_ELEMENT_CLASS[attr_pair_1[0]](None, qn1)
                    if qn2 not in node_map:
                        node_map[qn2] = INFERRED_ELEMENT_CLASS[attr_pair_2[0]](None, qn2)
                except KeyError:
                    # Unsupported attribute; cannot infer the type of the element
                    warnings.append(f"Skipping unsupported attribute: {attr_pair_1[0]} or {attr_pair_2[0]}")
                    continue  # skipping this relation
                if qn1 not in node_relations:
                    node_relations[qn1] = []
                if qn2 not in node_relations:
                    node_relations[qn2] = []
                node_relations[qn1].append(DirectedRelation(source=qn1, target=qn2, relation=relation))
                node_relations[qn2].append(DirectedRelation(source=qn2, target=qn1, relation=relation))
            else:
                warnings.append(f"Relation {relation} has invalid or missing identifiers: {qn1}, {qn2}")

        result_nodes = set()
        result_relations = set()
        visited = set()
        queue = [(eid, direction) for eid in entity_ids]
        while queue:
            current_id, current_direction = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)
            if current_id not in node_map:
                # TODO: remove warning?
                warnings.append(f"Entity ID '{current_id}' has no relations in the document.")
                continue

            current_node = node_map[current_id]
            result_nodes.add(current_node)

            # Add all relations for the current node
            if current_id in node_relations:
                for relation in node_relations[current_id]:
                    add = False
                    if current_id == relation["source"]:  # Relation is downstream
                        if current_direction == DocumentSubgraphDirection.FORWARD or current_direction == DocumentSubgraphDirection.BOTH:
                            add = True
                    elif current_id == relation["target"]:  # Relation is upstream
                        if current_direction == DocumentSubgraphDirection.BACKWARD or current_direction == DocumentSubgraphDirection.BOTH:
                            add = True
                    if add:
                        if relation["target"] not in visited:
                            queue.append((relation["target"], current_direction))
                        result_relations.add(relation["relation"])

        # Add the collected nodes and relations to the new document
        for node in result_nodes:
            new_doc.add_record(node)
        for relation in result_relations:
            new_doc.add_record(relation)

        # Serialize the new document to a dictionary
        serialized = json.loads(new_doc.serialize())

        return warnings, serialized
