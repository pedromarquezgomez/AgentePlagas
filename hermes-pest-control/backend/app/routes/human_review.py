from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.admin_auth import require_admin_auth
from app.schemas.human_review import HumanReviewItemUpdate
from app.services.human_review_service import (
    HumanReviewItemNotFoundError,
    HumanReviewService,
)

router = APIRouter(
    prefix="/human-review",
    tags=["human-review"],
    dependencies=[Depends(require_admin_auth)],
)
human_review_service = HumanReviewService()


@router.get("")
async def list_review_items(
    status: str | None = None,
    priority: str | None = None,
    limit: int | None = Query(default=50, ge=1, le=200),
) -> list[dict]:
    return await human_review_service.list_review_items(
        status_filter=status,
        priority=priority,
        limit=limit,
    )


@router.get("/{item_id}")
async def get_review_item(item_id: str) -> dict:
    try:
        return await human_review_service.get_review_item(item_id)
    except HumanReviewItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Human review item not found.",
        ) from exc


@router.patch("/{item_id}")
async def update_review_item(
    item_id: str,
    review_update: HumanReviewItemUpdate,
) -> dict:
    updates = review_update.model_dump(exclude_unset=True)
    try:
        return await human_review_service.update_review_item(item_id, updates)
    except HumanReviewItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Human review item not found.",
        ) from exc
