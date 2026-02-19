import logging

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from application.documentation.openapi_generation import EXAMPLE_UUID, EXAMPLE_UUID_2
from application.exceptions.responses import EXCEPTION_SCHEMA
from application.exceptions.types import NotFoundException, ForbiddenException, ServiceUnavailableException, BadRequestException
from models import PidType
from routers.common.dependencies import LoggedUser
from services.artifact_storage.service import ArtifactRecordStorageService
from services.pid.service import PidService

__all__ = ("router",)

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="",
    route_class=DishkaRoute
)


class RelatedPidsGet(BaseModel):
    pid: str = Field(..., examples=[EXAMPLE_UUID], description="PID of the artifact.")
    related_pids: list[str] = Field(default_factory=list, examples=[[EXAMPLE_UUID_2]], description="List of related PIDs.")


class RelatedPidsPatch(BaseModel):
    related_pids: list[str] = Field(..., examples=[[EXAMPLE_UUID_2]], description="List of PIDs to add as related to this artifact.")


documentation_get = {
    "summary": "List Artifact Related PIDs",
    "description": "This endpoint retrieves the list of related PIDs for a specific artifact PID.",
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns the current list of related PIDs for the specified artifact.",
    "responses": {
        status.HTTP_404_NOT_FOUND: EXCEPTION_SCHEMA[NotFoundException, "The specified artifact PID does not exist."],
        status.HTTP_503_SERVICE_UNAVAILABLE: EXCEPTION_SCHEMA[ServiceUnavailableException]
    }
}


@router.get("/{pid:path}/related", **documentation_get)
async def list_related_pids(
    pid: str,
    artifact_record_storage: FromDishka[ArtifactRecordStorageService],
    pid_service: FromDishka[PidService],
) -> RelatedPidsGet:
    await artifact_record_storage.get_artifact_by_pid(pid)

    pid_record = await pid_service.get_pid_record(pid)
    if pid_record.type != PidType.ARTIFACT:
        raise BadRequestException(f"PID '{pid}' is not an artifact PID.")

    return RelatedPidsGet(
        pid=pid,
        related_pids=pid_record.related_pids or []
    )


documentation_patch = {
    "summary": "Add Artifact Related PIDs",
    "description": "This endpoint adds a list of PIDs to the related PIDs of a specific artifact.",
    "status_code": status.HTTP_200_OK,
    "response_description": "Returns the updated list of related PIDs for the specified artifact.",
    "responses": {
        status.HTTP_400_BAD_REQUEST: EXCEPTION_SCHEMA[BadRequestException],
        status.HTTP_403_FORBIDDEN: EXCEPTION_SCHEMA[ForbiddenException, "You do not have permission to update related PIDs for this artifact."],
        status.HTTP_404_NOT_FOUND: EXCEPTION_SCHEMA[NotFoundException, "The specified artifact PID does not exist."],
        status.HTTP_503_SERVICE_UNAVAILABLE: EXCEPTION_SCHEMA[ServiceUnavailableException]
    }
}


@router.patch("/{pid:path}/related", **documentation_patch)
async def add_related_pids(
    pid: str,
    payload: RelatedPidsPatch,
    artifact_record_storage: FromDishka[ArtifactRecordStorageService],
    pid_service: FromDishka[PidService],
    logged_user: LoggedUser,
    allow_external_pids: bool = False
) -> RelatedPidsGet:
    artifact_record = await artifact_record_storage.get_artifact_by_pid(pid)

    if artifact_record.owner_id != logged_user.id:
        raise ForbiddenException("You do not have permission to update related PIDs for this artifact.")

    pid_record = await pid_service.get_pid_record(pid)
    if pid_record.type != PidType.ARTIFACT:
        raise BadRequestException(f"PID '{pid}' is not an artifact PID.")

    existing_related = pid_record.related_pids or []
    existing_set = set(existing_related)
    for related_pid in payload.related_pids:
        if related_pid == pid:
            raise BadRequestException("A PID cannot be related to itself.")
        if not allow_external_pids:
            related_pid_record = await pid_service.get_pid_record(related_pid, raise_not_found=False)
            if not related_pid_record:
                raise BadRequestException(
                    f"Related PID '{related_pid}' record does not exist. If you are trying " +
                    "to relate an external PID, set 'allow_external_pids' to true."
                )
        if related_pid not in existing_set:
            existing_related.append(related_pid)
            existing_set.add(related_pid)

    pid_record.related_pids = existing_related
    pid_record = await pid_service.update_pid_record(pid_record)

    return RelatedPidsGet(
        pid=pid_record.pid,
        related_pids=pid_record.related_pids or []
    )
