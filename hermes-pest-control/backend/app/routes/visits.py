from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.admin_auth import require_admin_auth
from app.schemas.visit import VisitCreate, VisitUpdate
from app.services.visit_service import VisitNotFoundError, VisitService

router = APIRouter(
    prefix="/visits",
    tags=["visits"],
    dependencies=[Depends(require_admin_auth)],
)
visit_service = VisitService()


@router.get("")
async def list_visits(
    incident_id: str | None = None,
    technician_id: str | None = None,
    status: str | None = None,
    limit: int | None = Query(default=50, ge=1, le=200),
) -> list[dict]:
    return await visit_service.list_visits(
        incident_id=incident_id,
        technician_id=technician_id,
        status_filter=status,
        limit=limit,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_visit(visit_create: VisitCreate) -> dict:
    visit = await visit_service.create_visit(visit_create)
    return visit.model_dump()


@router.get("/{visit_id}")
async def get_visit(visit_id: str) -> dict:
    try:
        return await visit_service.get_visit(visit_id)
    except VisitNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found.",
        ) from exc


@router.patch("/{visit_id}")
async def update_visit(
    visit_id: str,
    visit_update: VisitUpdate,
) -> dict:
    updates = visit_update.model_dump(exclude_unset=True)
    try:
        return await visit_service.update_visit(visit_id, updates)
    except VisitNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found.",
        ) from exc
