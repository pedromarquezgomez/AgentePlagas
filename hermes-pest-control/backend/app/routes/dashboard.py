from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends

from app.dependencies.admin_auth import require_admin_auth
from app.schemas.dashboard import DashboardSummary
from app.services.human_review_service import HumanReviewService
from app.services.incident_service import IncidentService
from app.services.technician_service import TechnicianService
from app.services.visit_service import VisitService

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(require_admin_auth)],
)

incident_service = IncidentService()
human_review_service = HumanReviewService()
visit_service = VisitService()
technician_service = TechnicianService()

DASHBOARD_LIMIT = 1000


def _count_by(items: list[dict], field: str, value: object) -> int:
    return sum(1 for item in items if item.get(field) == value)


def _scheduled_date(item: dict) -> date | None:
    value = item.get("scheduled_start")
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None


def _count_visits_on_date(items: list[dict], target_date: date) -> int:
    return sum(1 for item in items if _scheduled_date(item) == target_date)


def _count_scheduled_visits_in_week(items: list[dict], today: date) -> int:
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return sum(
        1
        for item in items
        if item.get("status") == "scheduled"
        and (visit_date := _scheduled_date(item)) is not None
        and start_of_week <= visit_date <= end_of_week
    )


@router.get("/summary")
async def get_dashboard_summary() -> dict:
    incidents = await incident_service.list_incidents(limit=DASHBOARD_LIMIT)
    review_items = await human_review_service.list_review_items(limit=DASHBOARD_LIMIT)
    visits = await visit_service.list_visits(limit=DASHBOARD_LIMIT)
    technicians = await technician_service.list_technicians(limit=DASHBOARD_LIMIT)
    today = date.today()

    summary = DashboardSummary(
        incidents={
            "total": len(incidents),
            "pending_review": _count_by(incidents, "status", "pending_review"),
            "urgent": _count_by(incidents, "priority", "urgent"),
            "ready_for_scheduling": _count_by(
                incidents,
                "status",
                "ready_for_scheduling",
            ),
            "urgent_24h": _count_by(incidents, "dispatch_bucket", "URGENT_24H"),
            "human_review": _count_by(incidents, "dispatch_bucket", "MANUAL_REVIEW"),
            "high_priority": _count_by(incidents, "operational_priority", "HIGH"),
            "pending_this_week": _count_by(incidents, "dispatch_bucket", "THIS_WEEK"),
        },
        human_review={
            "open": _count_by(review_items, "status", "open"),
            "urgent": _count_by(review_items, "priority", "urgent"),
        },
        visits={
            "total": len(visits),
            "scheduled": _count_by(visits, "status", "scheduled"),
            "in_progress": _count_by(visits, "status", "in_progress"),
            "completed": _count_by(visits, "status", "completed"),
            "today": _count_visits_on_date(visits, today),
            "scheduled_this_week": _count_scheduled_visits_in_week(visits, today),
        },
        technicians={
            "total": len(technicians),
            "active": _count_by(technicians, "active", True),
        },
    )
    return summary.model_dump()
