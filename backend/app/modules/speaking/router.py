"""Speaking route composition."""

from fastapi import APIRouter

from app.modules.speaking.mock import router as mock_router
from app.modules.speaking.practice import router as practice_router

router = APIRouter()
router.include_router(practice_router)
router.include_router(mock_router)
