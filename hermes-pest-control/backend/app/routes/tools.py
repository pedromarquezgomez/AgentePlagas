from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.admin_auth import require_admin_auth
from app.schemas.tool_harness import ToolExecutionRecordUpdate
from app.services.gmail_tool_executor import (
    GmailToolDisabledError,
    GmailToolExecutionError,
    GmailToolPayloadError,
)
from app.services.tool_execution_service import (
    ToolExecutionAlreadyExecutedError,
    ToolExecutionNotApprovedError,
    ToolExecutionRecordNotFoundError,
    ToolExecutionService,
    ToolExecutionUnsupportedError,
)

router = APIRouter(
    prefix="/tools",
    tags=["tools"],
    dependencies=[Depends(require_admin_auth)],
)
tool_execution_service = ToolExecutionService()
gmail_tool_executor = None


@router.get("/executions")
async def list_tool_executions(
    status: str | None = None,
    tool_name: str | None = None,
    provider: str | None = None,
    decision: str | None = None,
    risk_level: int | None = Query(default=None, ge=0, le=5),
    requires_approval: bool | None = None,
    limit: int | None = Query(default=50, ge=1, le=200),
) -> list[dict]:
    return await tool_execution_service.list_execution_records(
        review_status=status,
        tool_name=tool_name,
        provider=provider,
        decision=decision,
        risk_level=risk_level,
        requires_approval=requires_approval,
        limit=limit,
    )


@router.get("/executions/{execution_id}")
async def get_tool_execution(execution_id: str) -> dict:
    try:
        return await tool_execution_service.get_execution_record(execution_id)
    except ToolExecutionRecordNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool execution record not found.",
        ) from exc


@router.patch("/executions/{execution_id}")
async def update_tool_execution(
    execution_id: str,
    execution_update: ToolExecutionRecordUpdate,
) -> dict:
    try:
        return await tool_execution_service.update_execution_record(
            execution_id,
            execution_update,
        )
    except ToolExecutionRecordNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool execution record not found.",
        ) from exc


@router.post("/executions/{execution_id}/execute")
async def execute_tool_execution(execution_id: str) -> dict:
    try:
        return await tool_execution_service.execute_execution_record(
            execution_id,
            gmail_executor=gmail_tool_executor,
        )
    except ToolExecutionRecordNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool execution record not found.",
        ) from exc
    except (
        ToolExecutionNotApprovedError,
        ToolExecutionAlreadyExecutedError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (ToolExecutionUnsupportedError, GmailToolPayloadError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except GmailToolDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except GmailToolExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gmail draft execution failed.",
        ) from exc
