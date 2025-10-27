from fastapi import APIRouter

from ._register import router as register_router
from ._login import router as login_router
from ._verify import router as verify_router

__all__ = ("router",)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

# Include the sub-routers for registration and login
router.include_router(register_router)
router.include_router(login_router)
router.include_router(verify_router)
