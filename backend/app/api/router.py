from fastapi import APIRouter

from app.api.deals import router as deals_router
from app.api.health import router as health_router
from app.api.imports import router as imports_router
from app.api.review import router as review_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(imports_router)
api_router.include_router(review_router)
api_router.include_router(deals_router)
