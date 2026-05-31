from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.admin_auth import require_admin_auth
from app.schemas.technician import TechnicianCreate, TechnicianUpdate
from app.services.technician_service import TechnicianNotFoundError, TechnicianService

router = APIRouter(
    prefix="/technicians",
    tags=["technicians"],
    dependencies=[Depends(require_admin_auth)],
)
technician_service = TechnicianService()


@router.get("")
async def list_technicians(
    active: bool | None = None,
    limit: int | None = Query(default=50, ge=1, le=200),
) -> list[dict]:
    return await technician_service.list_technicians(
        active=active,
        limit=limit,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_technician(technician_create: TechnicianCreate) -> dict:
    technician = await technician_service.create_technician(technician_create)
    return technician.model_dump()


@router.get("/{technician_id}")
async def get_technician(technician_id: str) -> dict:
    try:
        return await technician_service.get_technician(technician_id)
    except TechnicianNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Technician not found.",
        ) from exc


@router.patch("/{technician_id}")
async def update_technician(
    technician_id: str,
    technician_update: TechnicianUpdate,
) -> dict:
    updates = technician_update.model_dump(exclude_unset=True)
    try:
        return await technician_service.update_technician(technician_id, updates)
    except TechnicianNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Technician not found.",
        ) from exc
