import logging

from fastapi import APIRouter, status
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.documentation.openapi_generation import EXAMPLE_UUID
from services.pid.service import PidService
from application.settings import PID_ADMIN_HANDLE, PID_ADMIN_HANDLE_INDEX, PID_ADMIN_HANDLE_PERMISSIONS

__all__ = ("router",)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="",
    route_class=DishkaRoute
)

documentation = {
    "summary": "Retrieve a specific PID Record from the PID Service",
    "description": "This endpoint retrieves a specific PID record from the PID service.",
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns the requested PID record.",
    "responses": {
        status.HTTP_200_OK: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "responseCode": 1,
                        "handle": f"{EXAMPLE_UUID}",
                        "values": [
                            {
                                "index": 100,
                                "type": "HS_ADMIN",
                                "data": {
                                    "format": "admin",
                                    "value": {
                                        "handle": PID_ADMIN_HANDLE,
                                        "index": PID_ADMIN_HANDLE_INDEX,
                                        "permissions": PID_ADMIN_HANDLE_PERMISSIONS,
                                    }
                                },
                                "ttl": 86400,
                                "timestamp": "2025-04-25T16:05:27Z"
                            },
                            {
                                "index": 1,
                                "type": "URL",
                                "data": {
                                    "format": "string",
                                    "value": "http://example.com/document/12345"
                                },
                                "ttl": 86400,
                                "timestamp": "2025-04-25T16:05:27Z"
                            }
                        ],
                    }
                }
            }
        }
    }
}


@router.get("/{prefix}/{pid}", **documentation)
async def get_pid_prefix(
    pid: str,
    prefix: str,
    pid_service: FromDishka[PidService]
) -> dict:
    """
    Endpoint to retrieve a specific PID record from the PID service.
    This endpoint retrieves the PID record for the specified PID.
    """

    pid = f"{prefix}/{pid}"
    record_pid = await pid_service.get_document_pid(pid)

    return record_pid
