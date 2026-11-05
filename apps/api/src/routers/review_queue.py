"""API router for managing the Human Review Queue."""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.auth.deps import get_current_org, get_current_user
from apps.api.src.db.session import get_db
from apps.api.src.models.review_queue import ReviewQueueItem
from apps.api.src.models.user import User

router = APIRouter(prefix="/review-queue", tags=["review-queue"])


class ReviewQueueItemSummary(BaseModel):
    id: uuid.UUID
    query: str
    answer: str
    trigger_reason: str
    confidence_score: float | None
    status: str
    created_at: str
    reviewed_by: str | None


class ReviewQueueItemDetail(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    trace_id: uuid.UUID | None
    query: str
    answer: str
    retrieved_chunks: list[dict[str, Any]]
    trigger_reason: str
    confidence_score: float | None
    status: str
    edited_answer: str | None
    reviewed_by: str | None
    reviewed_at: str | None
    notes: str | None
    created_at: str
    updated_at: str


class ReviewActionRequest(BaseModel):
    action: Literal["accept", "reject", "edit"] = Field(
        ..., description="Action to apply: 'accept', 'reject', or 'edit'"
    )
    edited_answer: str | None = Field(None, description="Updated answer if action is 'edit'")
    notes: str | None = Field(None, max_length=1000, description="Optional reviewer notes")


@router.get("", response_model=list[ReviewQueueItemSummary])
async def list_review_queue(
    status_filter: str | None = Query(
        "all", description="Status filter: 'pending', 'accepted', 'rejected', 'edited', 'all'"
    ),
    limit: int = Query(50, ge=1, le=100),
    current_org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[ReviewQueueItemSummary]:
    """Lists review queue items for the authenticated organization."""
    stmt = select(ReviewQueueItem).where(ReviewQueueItem.org_id == current_org_id)

    if status_filter and status_filter.lower() != "all":
        stmt = stmt.where(ReviewQueueItem.status == status_filter.lower())

    stmt = stmt.order_by(desc(ReviewQueueItem.created_at)).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return [
        ReviewQueueItemSummary(
            id=item.id,
            query=item.query,
            answer=item.edited_answer or item.answer,
            trigger_reason=item.trigger_reason,
            confidence_score=item.confidence_score,
            status=item.status,
            created_at=item.created_at.isoformat(),
            reviewed_by=item.reviewed_by,
        )
        for item in items
    ]


@router.get("/{item_id}", response_model=ReviewQueueItemDetail)
async def get_review_queue_item(
    item_id: uuid.UUID,
    current_org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> ReviewQueueItemDetail:
    """Retrieves full details of a single review queue item."""
    stmt = select(ReviewQueueItem).where(
        ReviewQueueItem.id == item_id,
        ReviewQueueItem.org_id == current_org_id,
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review queue item not found",
        )

    return ReviewQueueItemDetail(
        id=item.id,
        org_id=item.org_id,
        trace_id=item.trace_id,
        query=item.query,
        answer=item.answer,
        retrieved_chunks=item.retrieved_chunks,
        trigger_reason=item.trigger_reason,
        confidence_score=item.confidence_score,
        status=item.status,
        edited_answer=item.edited_answer,
        reviewed_by=item.reviewed_by,
        reviewed_at=item.reviewed_at.isoformat() if item.reviewed_at else None,
        notes=item.notes,
        created_at=item.created_at.isoformat(),
        updated_at=item.updated_at.isoformat(),
    )


@router.post("/{item_id}/action", response_model=ReviewQueueItemDetail)
async def process_review_action(
    item_id: uuid.UUID,
    payload: ReviewActionRequest,
    current_org_id: uuid.UUID = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewQueueItemDetail:
    """Applies human review decisions (accept, reject, or edit) to a queued item."""
    stmt = select(ReviewQueueItem).where(
        ReviewQueueItem.id == item_id,
        ReviewQueueItem.org_id == current_org_id,
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review queue item not found",
        )

    if payload.action == "edit":
        if not payload.edited_answer or not payload.edited_answer.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="edited_answer is required when action is 'edit'",
            )
        item.status = "edited"
        item.edited_answer = payload.edited_answer.strip()
    elif payload.action == "accept":
        item.status = "accepted"
    elif payload.action == "reject":
        item.status = "rejected"

    item.reviewed_by = current_user.email
    item.reviewed_at = datetime.now(UTC)
    item.notes = payload.notes

    await db.commit()
    await db.refresh(item)

    return ReviewQueueItemDetail(
        id=item.id,
        org_id=item.org_id,
        trace_id=item.trace_id,
        query=item.query,
        answer=item.answer,
        retrieved_chunks=item.retrieved_chunks,
        trigger_reason=item.trigger_reason,
        confidence_score=item.confidence_score,
        status=item.status,
        edited_answer=item.edited_answer,
        reviewed_by=item.reviewed_by,
        reviewed_at=item.reviewed_at.isoformat() if item.reviewed_at else None,
        notes=item.notes,
        created_at=item.created_at.isoformat(),
        updated_at=item.updated_at.isoformat(),
    )
