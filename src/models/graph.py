from enum import Enum
from dataclasses import dataclass


class DocumentSubgraphDirection(Enum):
    """
    Enum representing the direction of the document subgraph.
    """
    BOTH = "both"
    FORWARD = "forward"
    BACKWARD = "backward"


@dataclass
class DocumentGraphEntity:
    """
    Represents an entity or relation in the document graph.
    Returned by the graph list operation.
    """

    id: str
    type: str
    group: str
    is_element: bool
    is_relation: bool
    data: dict[str, str]
