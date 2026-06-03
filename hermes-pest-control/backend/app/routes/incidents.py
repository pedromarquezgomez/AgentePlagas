from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.admin_auth import require_admin_auth
from app.schemas.incident import IncidentUpdate
from app.services.incident_service import IncidentNotFoundError, IncidentService

router = APIRouter(
    prefix="/incidents",
    tags=["incidents"],
    dependencies=[Depends(require_admin_auth)],
)
incident_service = IncidentService()


@router.get("")
async def list_incidents(
    status: str | None = None,
    priority: str | None = None,
    pest_type: str | None = None,
    dispatch_bucket: str | None = None,
    sla_status: str | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    limit: int | None = Query(default=50, ge=1, le=200),
) -> list[dict]:
    return await incident_service.list_incidents(
        status_filter=status,
        priority=priority,
        pest_type=pest_type,
        dispatch_bucket=dispatch_bucket,
        sla_status=sla_status,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
    )


@router.get("/{incident_id}")
async def get_incident(incident_id: str) -> dict:
    try:
        return await incident_service.get_incident(incident_id)
    except IncidentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        ) from exc


@router.patch("/{incident_id}")
async def update_incident(incident_id: str, incident_update: IncidentUpdate) -> dict:
    updates = incident_update.model_dump(exclude_unset=True)
    try:
        return await incident_service.update_incident(incident_id, updates)
    except IncidentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        ) from exc
