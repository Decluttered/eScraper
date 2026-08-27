from fastapi import APIRouter

from app.api.alerts import router as alerts_router
from app.api.deals import router as deals_router
from app.api.health import router as health_router
from app.api.imports import router as imports_router
from app.api.inventory import router as inventory_router
from app.api.review import router as review_router
from app.api.settings import router as settings_router
from app.api.source_health import router as source_health_router
from app.api.watchlists import router as watchlists_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(imports_router)
api_router.include_router(review_router)
api_router.include_router(deals_router)
api_router.include_router(watchlists_router)
api_router.include_router(settings_router)
api_router.include_router(inventory_router)
api_router.include_router(alerts_router)
api_router.include_router(source_health_router)
