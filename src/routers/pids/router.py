from fastapi import APIRouter

from ._list import router as list_router
from ._get import router as get_router


pids_router = APIRouter(
    prefix="",
    tags=["PID Service Proxy"],
)


# Include the sub-routers for listing and creating documents
pids_router.include_router(list_router)

pid_router = APIRouter(
    prefix="/pids",
    tags=["PID Service Proxy"],
)

# Include the sub-routers for listing all PIDs
pid_router.include_router(get_router)

pids_router.include_router(pid_router)
