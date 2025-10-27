from pydantic import BaseModel, Field
from fastapi import APIRouter, status, Query
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.exceptions.responses import EXCEPTION_SCHEMA
from application.exceptions.types import NotFoundException, ServiceUnavailableException
from services.document_storage.service import DocumentRecordStorageService
from services.graph.service import GraphService


router = APIRouter(
    prefix="",
    route_class=DishkaRoute
)


class DocumentGraphEntityGet(BaseModel):
    """
    Represents the response format for a list operation on a provenance document graph.
    """
    id: str = Field(description="Unique identifier of the graph entity (may be empty if `_` is used as identifier).", examples=[""])
    type: str = Field(description="The type of the graph entity", examples=["wasDerivedFrom", "entity", "agent", "activity", "used"])
    group: str = Field(description="The group of the graph entity", examples=["prov:Derivation", "prov:Entity", "prov:Activity", "prov:Agent", "prov:Usage"])
    is_element: bool = Field(description="Indicates if the entity is a graph element", examples=[False, False])
    is_relation: bool = Field(description="Indicates if the entity is a graph relation", examples=[True, False])
    data: dict[str, str] = Field(
        default_factory=dict,
        description="A dictionary containing the attributes of the graph entity.",
        examples=[{"prov:entity": "now:entity-article-v1.html", "prov:activity": "is:writeArticle"}]
    )


class DocumentGraphListResponse(BaseModel):
    """
    Response model for listing elements in a provenance document graph.
    """
    warnings: list[str] = Field(default_factory=list, description="List of warnings encountered during the operation.")
    elements: list[DocumentGraphEntityGet] = Field(
        default_factory=list,
        description="List of elements in the provenance document graph."
    )


documentation = {
    "summary": "List elements in a Provenance Document Graph",
    "description": ("This endpoint retrieves a list of elements in a provenance document graph based on the entity type and ids."
                    " Empty `entity_ids` or `entity_types` will not filter the results."),
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns a list of filtered elements in the provenance document graph.",
    "responses": {
        # TODO: Add more specific error responses as needed
        status.HTTP_404_NOT_FOUND: EXCEPTION_SCHEMA[NotFoundException, "The specified document PID does not exist."],
        status.HTTP_503_SERVICE_UNAVAILABLE: EXCEPTION_SCHEMA[ServiceUnavailableException]
    }
}


@router.get("/list", **documentation)
async def list_graphs(
    pid: str,
    prefix: str,
    graph_service: FromDishka[GraphService],
    document_storage_service: FromDishka[DocumentRecordStorageService],
    entity_types: list[str] = Query(None, description="List of entity types to filter the results."),
    entity_ids: list[str] = Query(None, description="List of entity IDs to filter the results."),
    is_element: bool | None = Query(None, description="Filter by whether the entity is an element."),
    is_relation: bool | None = Query(None, description="Filter by whether the entity is a relation.")
) -> DocumentGraphListResponse:
    """
    Perform list operation on a provenance document graph
    """
    if entity_ids is None:
        entity_ids = []
    if entity_types is None:
        entity_types = []

    pid = f"{prefix}/{pid}"

    document_record = await document_storage_service.get_document_by_pid(pid)

    # Fetch the graph elements based on the provided entity types and ids
    warnings, elements = await graph_service.list_elements(document_record, entity_ids, entity_types, is_element, is_relation)
    return DocumentGraphListResponse(warnings=warnings, elements=[
        DocumentGraphEntityGet(
            id=element.id,
            type=element.type,
            group=element.group,
            data=element.data,
            is_element=element.is_element,
            is_relation=element.is_relation
        )
        for element in elements
    ])
