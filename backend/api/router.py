# backend/api/router.py

from fastapi import APIRouter

from .routes.health import router as health_router
from .routes.metadata import router as metadata_router
from .routes.field import router as field_router
from .routes.profile import router as profile_router
from .routes.tchp import router as tchp_router
from .routes.d26 import router as d26_router
from .routes.mld import router as mld_router
from .routes.thermocline import router as thermocline_router
from .routes.uncertainty import router as uncertainty_router
from .routes.sampling import router as sampling_router


router = APIRouter(
    prefix="/api/v1/ocean",
)


router.include_router(health_router)
router.include_router(metadata_router)
router.include_router(field_router)
router.include_router(profile_router)
router.include_router(tchp_router)
router.include_router(d26_router)
router.include_router(mld_router)
router.include_router(thermocline_router)
router.include_router(uncertainty_router)
router.include_router(sampling_router)