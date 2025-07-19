import logging

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.documentation.openapi_generation import EXAMPLE_UUID, EXAMPLE_UUID_2
from services.pid.service import PidService

__all__ = ("router",)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/pids",
    route_class=DishkaRoute
)

documentation = {
    "summary": "List All PID Records stored in PID Service",
    "description": "This endpoint retrieves a list of all paginated pids available in the PID service. Default page size is 10, and pagination starts from page 0.",
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns a list of document PIDs stored in the PID service.",
    "responses": {
        status.HTTP_200_OK: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": [
                        EXAMPLE_UUID,
                        EXAMPLE_UUID_2
                    ]
                }
            }
        }
    }
}


@router.get("", **documentation)
async def list_pids(
    pid_service: FromDishka[PidService],
    page: int = 0,
    page_size: int = 10
) -> list[str]:
    """
    Endpoint to list all document records available in the storage.
    This endpoint retrieves all document records and returns them in a standardized format.
    """

    record_pids = await pid_service.list_document_pids(page=page, page_size=page_size)

    return record_pids
