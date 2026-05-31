from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.admin_auth import require_admin_auth
from app.services.decision_audit_service import (
    DecisionAuditService,
    DecisionRecordNotFoundError,
)

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(require_admin_auth)],
)
decision_audit_service = DecisionAuditService()


@router.get("/decisions")
async def list_decision_records(
    conversation_id: str | None = None,
    action_type: str | None = None,
    fallback_used: bool | None = None,
    limit: int | None = Query(default=50, ge=1, le=200),
) -> list[dict]:
    return await decision_audit_service.list_decision_records(
        conversation_id=conversation_id,
        action_type=action_type,
        fallback_used=fallback_used,
        limit=limit,
    )


@router.get("/decisions/{decision_id}")
async def get_decision_record(decision_id: str) -> dict:
    try:
        return await decision_audit_service.get_decision_record(decision_id)
    except DecisionRecordNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision record not found.",
        ) from exc
