import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.evaluation import EvaluationSnapshotModel
from app.db.models.listing import ListingObservationModel, RawListingModel
from app.db.session import get_session
from app.domain.enums import ConfidenceLevel, Recommendation
from app.schemas.deals import DealDetail, DealListItem

router = APIRouter(prefix="/deals", tags=["deals"])


async def _latest_snapshots_per_observation(
    session: AsyncSession,
) -> list[EvaluationSnapshotModel]:
    from sqlalchemy import func

    subquery = (
        select(
            EvaluationSnapshotModel.observation_id,
            func.max(EvaluationSnapshotModel.created_at).label("latest"),
        )
        .group_by(EvaluationSnapshotModel.observation_id)
        .subquery()
    )
    stmt = select(EvaluationSnapshotModel).join(
        subquery,
        (EvaluationSnapshotModel.observation_id == subquery.c.observation_id)
        & (EvaluationSnapshotModel.created_at == subquery.c.latest),
    )
    return (await session.scalars(stmt)).all()


@router.get("", response_model=list[DealListItem])
async def list_deals(
    session: Annotated[AsyncSession, Depends(get_session)],
    recommendation: Recommendation | None = Query(default=None),
    category: str | None = Query(default=None),
    source: str | None = Query(default=None),
    confidence: ConfidenceLevel | None = Query(default=None),
    minimum_profit_cents: int | None = Query(default=None, ge=0),
    sort: Literal["score", "profit", "roi", "evaluated_at"] = "score",
) -> list[DealListItem]:
    snapshots = await _latest_snapshots_per_observation(session)
    items: list[DealListItem] = []
    for snap in snapshots:
        observation = await session.scalar(
            select(ListingObservationModel).where(
                ListingObservationModel.id == snap.observation_id
            )
        )
        if observation is None:
            continue
        raw = await session.scalar(
            select(RawListingModel).where(
                RawListingModel.id == observation.raw_listing_id
            )
        )
        if raw is None:
            continue
        if recommendation is not None and snap.recommendation is not recommendation:
            continue
        if confidence is not None and snap.market_confidence is not confidence:
            continue
        if source is not None and raw.source.value != source:
            continue
        if minimum_profit_cents is not None and snap.expected_profit_cents < minimum_profit_cents:
            continue
        landed = observation.asking_price_cents + observation.shipping_cents
        items.append(
            DealListItem(
                evaluation_id=snap.id,
                observation_id=snap.observation_id,
                title=raw.raw_title,
                asking_landed_cents=landed,
                expected_profit_cents=snap.expected_profit_cents,
                downside_profit_cents=snap.downside_profit_cents,
                maximum_purchase_price_cents=snap.maximum_purchase_price_cents,
                expected_roi_bps=snap.expected_roi_bps,
                score=snap.score,
                confidence=snap.market_confidence,
                recommendation=snap.recommendation,
                evaluated_at=snap.created_at,
            )
        )
    if sort == "profit":
        items.sort(key=lambda item: item.expected_profit_cents, reverse=True)
    elif sort == "roi":
        items.sort(key=lambda item: item.expected_roi_bps, reverse=True)
    elif sort == "evaluated_at":
        items.sort(key=lambda item: item.evaluated_at, reverse=True)
    else:
        items.sort(key=lambda item: item.score, reverse=True)
    return items


@router.get("/{evaluation_id}", response_model=DealDetail)
async def get_deal(
    evaluation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DealDetail:
    snap = await session.scalar(
        select(EvaluationSnapshotModel).where(
            EvaluationSnapshotModel.id == evaluation_id
        )
    )
    if snap is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    observation = await session.scalar(
        select(ListingObservationModel).where(
            ListingObservationModel.id == snap.observation_id
        )
    )
    if observation is None:
        raise HTTPException(status_code=404, detail="observation not found")
    raw = await session.scalar(
        select(RawListingModel).where(
            RawListingModel.id == observation.raw_listing_id
        )
    )
    if raw is None:
        raise HTTPException(status_code=404, detail="raw listing not found")
    landed = observation.asking_price_cents + observation.shipping_cents
    return DealDetail(
        evaluation_id=snap.id,
        observation_id=snap.observation_id,
        title=raw.raw_title,
        asking_landed_cents=landed,
        expected_profit_cents=snap.expected_profit_cents,
        downside_profit_cents=snap.downside_profit_cents,
        maximum_purchase_price_cents=snap.maximum_purchase_price_cents,
        expected_roi_bps=snap.expected_roi_bps,
        score=snap.score,
        confidence=snap.market_confidence,
        recommendation=snap.recommendation,
        evaluated_at=snap.created_at,
        source_url=raw.source_url,
        input_snapshot=dict(snap.input_snapshot),
        comparable_ids=list(snap.comparable_ids),
        reasons=list(snap.reasons),
        risk_reserve_cents=snap.risk_reserve_cents,
    )
