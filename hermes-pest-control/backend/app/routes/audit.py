from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.admin_auth import require_admin_auth
from app.services.decision_audit_service import (
    DecisionAuditService,
    DecisionRecordNotFoundError,
)
from app.services.shadow_decision_service import (
    ShadowDecisionRecordNotFoundError,
    ShadowDecisionService,
)

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(require_admin_auth)],
)
decision_audit_service = DecisionAuditService()
shadow_decision_service = ShadowDecisionService()


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


@router.get("/shadow-decisions")
async def list_shadow_decision_records(
    conversation_id: str | None = None,
    channel: str | None = None,
    shadow_action_type: str | None = None,
    limit: int | None = Query(default=50, ge=1, le=200),
) -> list[dict]:
    return await shadow_decision_service.list_shadow_records(
        conversation_id=conversation_id,
        channel=channel,
        shadow_action_type=shadow_action_type,
        limit=limit,
    )


@router.get("/shadow-decisions/{shadow_decision_id}")
async def get_shadow_decision_record(shadow_decision_id: str) -> dict:
    try:
        return await shadow_decision_service.get_shadow_record(shadow_decision_id)
    except ShadowDecisionRecordNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shadow decision record not found.",
        ) from exc
