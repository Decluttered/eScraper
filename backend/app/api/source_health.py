from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.evaluation import EvaluationSnapshotModel
from app.db.models.listing import ListingObservationModel
from app.db.models.operations import JobRunModel
from app.db.session import get_session

router = APIRouter(prefix="/source-health", tags=["source-health"])


@router.get("")
async def get_source_health(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    now = datetime.now(UTC)
    latest_snapshot = await session.scalar(
        select(EvaluationSnapshotModel).order_by(EvaluationSnapshotModel.created_at.desc()).limit(1)
    )
    last_success_at = latest_snapshot.created_at if latest_snapshot else None
    review_queue = await session.scalar(
        select(func.count())
        .select_from(ListingObservationModel)
        .where(ListingObservationModel.review_status == "PENDING")
    ) or 0
    failed_jobs = await session.scalar(
        select(func.count())
        .select_from(JobRunModel)
        .where(JobRunModel.status == "FAILED")
    ) or 0
    stale_estimate = 0
    if last_success_at:
        days = (now - last_success_at).days
        if days > 30:
            stale_estimate = 1
    return {
        "last_success_at": last_success_at.isoformat() if last_success_at else None,
        "quota_remaining": None,
        "stale_estimate_count": stale_estimate,
        "review_queue_count": review_queue,
        "failed_job_count": failed_jobs,
    }
