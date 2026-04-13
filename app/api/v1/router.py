"""API v1 router - aggregates all domain routers."""

from fastapi import APIRouter

from app.api.v1.announcement_gap import router as announcement_gap_router
from app.api.v1.health import router as health_router
from app.api.v1.scanner import router as scanner_router

router = APIRouter()

router.include_router(health_router)
router.include_router(scanner_router)
router.include_router(announcement_gap_router)
