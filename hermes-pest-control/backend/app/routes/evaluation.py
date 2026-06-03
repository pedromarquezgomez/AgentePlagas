from fastapi import APIRouter
from app.evaluation.runtime_stats import stats_collector

router = APIRouter(tags=["evaluation"])

@router.get("/evaluation/runtime-stats")
async def get_runtime_stats() -> dict:
    return stats_collector.get_stats()
