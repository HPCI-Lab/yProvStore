from pydantic import BaseModel, Field
from fastapi import APIRouter, status, Query
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from models import DocumentSubgraphDirection
from application.exceptions.responses import EXCEPTION_SCHEMA
from application.exceptions.types import NotFoundException, ServiceUnavailableException
from application.documentation.openapi_generation import EXAMPLE_DOCUMENT_DATA
from services.document_storage.service import DocumentRecordStorageService
from services.graph.service import GraphService


router = APIRouter(
    prefix="",
    route_class=DishkaRoute
)


class DocumentSubgraphResponse(BaseModel):
    """
    Response model for the subgraph operation on a provenance document graph.
    This model contains a list of warnings and the elements retrieved from the graph (which is a valid PROV JSON graph).
    """
    warnings: list[str] = Field(default_factory=list, description="List of warnings encountered during the operation.")
    subgraph: dict = Field(
        default_factory=dict,
        description="Elements retrieved from the provenance document graph, structured as a valid PROV JSON graph.",
        examples=[EXAMPLE_DOCUMENT_DATA]
    )


documentation = {
    "summary": "Retrieve Subgraph of Provenance Document Graph",
    "description": ("This endpoint retrieves a subgraph of elements in a provenance document graph based on the entity IDs."
                    " Empty `entity_ids` will not filter the results."),
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns a subgraph of elements in the provenance document graph.",
    "responses": {
        # TODO: Add more specific error responses as needed
        status.HTTP_404_NOT_FOUND: EXCEPTION_SCHEMA[NotFoundException, "The specified document PID does not exist."],
        status.HTTP_503_SERVICE_UNAVAILABLE: EXCEPTION_SCHEMA[ServiceUnavailableException]
    }
}


@router.get("/subgraph", **documentation)
async def subgraph(
    pid: str,
    graph_service: FromDishka[GraphService],
    document_storage_service: FromDishka[DocumentRecordStorageService],
    entity_ids: list[str] = Query(None, description="List of entity IDs to subgraph from."),
    direction: DocumentSubgraphDirection = Query(
        DocumentSubgraphDirection.BOTH,
        description="Direction of the subgraph operation. Defaults to BOTH."
    )
) -> DocumentSubgraphResponse:
    """
    Perform subgraph operation on a provenance document graph
    """
    if entity_ids is None:
        entity_ids = []

    document_record = await document_storage_service.get_document_by_pid(pid)

    # Fetch the graph elements based on the provided entity types and ids
    warnings, subgraph = await graph_service.subgraph(document_record, entity_ids, direction)
    return DocumentSubgraphResponse(warnings=warnings, subgraph=subgraph)
