from fastapi import APIRouter, status

from application.documentation.openapi_generation import EXAMPLE_METADATA_SCHEMA
from routers.metadata._get import DocumentMetadataGet


router = APIRouter(
    prefix="",
)


@router.get(
    "/metadata/schema",
    response_model=dict,
    summary="Return the JSON Schema for document metadata",
    responses={
        status.HTTP_200_OK: {"content": {"application/json": {"example": EXAMPLE_METADATA_SCHEMA}}},
    }
)
def get_metadata_schema():
    """
    Returns the JSON Schema for DocumentMetadataGet,
    so clients/CLIs can dynamically generate form fields and validate.
    """
    return DocumentMetadataGet.model_json_schema()
