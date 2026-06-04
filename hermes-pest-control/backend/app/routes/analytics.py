from fastapi import APIRouter, Depends

from app.analytics.contracts import BusinessMetrics
from app.analytics.service import AnalyticsService
from app.dependencies.admin_auth import require_admin_auth

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_admin_auth)],
)

analytics_service = AnalyticsService()


@router.get("/overview", response_model=BusinessMetrics)
async def get_analytics_overview() -> BusinessMetrics:
    return await analytics_service.get_metrics()
