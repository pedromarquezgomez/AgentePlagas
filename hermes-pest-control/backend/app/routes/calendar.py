from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.admin_auth import require_admin_auth
from app.services.visit_service import VisitService

router = APIRouter(
    prefix="/calendar",
    tags=["calendar"],
    dependencies=[Depends(require_admin_auth)],
)
visit_service = VisitService()


@router.get("/visits")
async def list_calendar_visits(
    start_date: date,
    end_date: date,
    technician_id: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[dict]:
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be greater than or equal to start_date.",
        )

    return await visit_service.list_calendar_visits(
        start_date=start_date,
        end_date=end_date,
        technician_id=technician_id,
        status_filter=status_filter,
    )
