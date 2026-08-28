from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.evaluation import EvaluationSnapshotModel
from app.db.models.listing import ListingObservationModel
from app.db.models.operations import JobRunModel
from app.db.session import get_session
from app.schemas.operations import SourceHealthOut

router = APIRouter(prefix="/source-health", tags=["source-health"])


def _latest_snapshot_subquery():
    row_number = (
        func.row_number()
        .over(
            partition_by=EvaluationSnapshotModel.observation_id,
            order_by=EvaluationSnapshotModel.created_at.desc(),
        )
        .label("row_number")
    )
    return select(EvaluationSnapshotModel, row_number).subquery()


@router.get("", response_model=SourceHealthOut)
async def get_source_health(session: AsyncSession = Depends(get_session)) -> SourceHealthOut:
    last_success_at = await session.scalar(
        select(func.max(JobRunModel.finished_at)).where(JobRunModel.status == "SUCCEEDED")
    )
    failed_job_count = await session.scalar(
        select(func.count()).select_from(JobRunModel).where(JobRunModel.status == "FAILED")
    )
    review_queue_count = await session.scalar(
        select(func.count())
        .select_from(ListingObservationModel)
        .where(ListingObservationModel.review_status == "PENDING")
    )

    latest = _latest_snapshot_subquery()
    stale_estimate_count = await session.scalar(
        select(func.count())
        .select_from(latest)
        .where(
            latest.c.row_number == 1,
            latest.c.reasons.contains(["market data is stale"]),
        )
    )

    return SourceHealthOut(
        last_success_at=last_success_at,
        quota_remaining=None,
        stale_estimate_count=stale_estimate_count or 0,
        review_queue_count=review_queue_count or 0,
        failed_job_count=failed_job_count or 0,
    )
