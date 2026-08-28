from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.evaluation import EvaluationSnapshotModel
from app.db.models.listing import ListingObservationModel, RawListingModel
from app.db.models.product import ProductModel
from app.db.session import get_session
from app.domain.enums import ConfidenceLevel, Marketplace, ProductCategory, Recommendation
from app.schemas.deals import DealDetail, DealListItem

router = APIRouter(prefix="/deals", tags=["deals"])

_SORT_COLUMNS = {
    "score": EvaluationSnapshotModel.score,
    "expected_profit_cents": EvaluationSnapshotModel.expected_profit_cents,
    "maximum_purchase_price_cents": EvaluationSnapshotModel.maximum_purchase_price_cents,
    "evaluated_at": EvaluationSnapshotModel.created_at,
}


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


@router.get("", response_model=list[DealListItem])
async def list_deals(
    recommendation: Recommendation | None = None,
    category: ProductCategory | None = None,
    source: Marketplace | None = None,
    confidence: ConfidenceLevel | None = None,
    minimum_profit_cents: int | None = Query(default=None),
    sort: str = Query(default="-score"),
    session: AsyncSession = Depends(get_session),
) -> list[DealListItem]:
    sort_key = sort.lstrip("-")
    if sort_key not in _SORT_COLUMNS:
        raise HTTPException(status_code=422, detail=f"unsupported sort field: {sort_key}")

    latest = _latest_snapshot_subquery()
    query = (
        select(
            latest.c.id.label("evaluation_id"),
            latest.c.observation_id,
            RawListingModel.raw_title,
            (
                ListingObservationModel.asking_price_cents
                + ListingObservationModel.shipping_cents
            ).label("asking_landed_cents"),
            latest.c.expected_profit_cents,
            latest.c.downside_profit_cents,
            latest.c.maximum_purchase_price_cents,
            latest.c.expected_roi_bps,
            latest.c.score,
            latest.c.market_confidence,
            latest.c.recommendation,
            latest.c.created_at.label("evaluated_at"),
        )
        .join(ListingObservationModel, ListingObservationModel.id == latest.c.observation_id)
        .join(RawListingModel, RawListingModel.id == ListingObservationModel.raw_listing_id)
        .join(ProductModel, ProductModel.id == ListingObservationModel.product_id)
        .where(latest.c.row_number == 1)
    )
    if recommendation is not None:
        query = query.where(latest.c.recommendation == recommendation)
    if confidence is not None:
        query = query.where(latest.c.market_confidence == confidence)
    if minimum_profit_cents is not None:
        query = query.where(latest.c.expected_profit_cents >= minimum_profit_cents)
    if category is not None:
        query = query.where(ProductModel.category == category)
    if source is not None:
        query = query.where(RawListingModel.source == source)

    sort_column = latest.c[sort_key]
    query = query.order_by(sort_column.desc() if sort.startswith("-") else sort_column.asc())

    rows = (await session.execute(query)).all()
    return [
        DealListItem(
            evaluation_id=row.evaluation_id,
            observation_id=row.observation_id,
            title=row.raw_title,
            asking_landed_cents=row.asking_landed_cents,
            expected_profit_cents=row.expected_profit_cents,
            downside_profit_cents=row.downside_profit_cents,
            maximum_purchase_price_cents=row.maximum_purchase_price_cents,
            expected_roi_bps=row.expected_roi_bps,
            score=row.score,
            confidence=row.market_confidence,
            recommendation=row.recommendation,
            evaluated_at=row.evaluated_at,
        )
        for row in rows
    ]


@router.get("/{evaluation_id}", response_model=DealDetail)
async def get_deal_detail(
    evaluation_id: UUID, session: AsyncSession = Depends(get_session)
) -> DealDetail:
    snapshot = await session.get(EvaluationSnapshotModel, evaluation_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="evaluation not found")
    observation = await session.get(ListingObservationModel, snapshot.observation_id)
    if observation is None:
        raise HTTPException(status_code=404, detail="observation not found")
    raw = await session.get(RawListingModel, observation.raw_listing_id)
    if raw is None:
        raise HTTPException(status_code=404, detail="raw listing not found")

    return DealDetail(
        evaluation_id=snapshot.id,
        observation_id=observation.id,
        title=raw.raw_title,
        asking_landed_cents=observation.asking_price_cents + observation.shipping_cents,
        expected_profit_cents=snapshot.expected_profit_cents,
        downside_profit_cents=snapshot.downside_profit_cents,
        maximum_purchase_price_cents=snapshot.maximum_purchase_price_cents,
        expected_roi_bps=snapshot.expected_roi_bps,
        score=snapshot.score,
        confidence=snapshot.market_confidence,
        recommendation=snapshot.recommendation,
        evaluated_at=snapshot.created_at,
        source_url=raw.source_url,
        input_snapshot=snapshot.input_snapshot,
        comparable_ids=snapshot.comparable_ids,
        reasons=snapshot.reasons,
        risk_reserve_cents=snapshot.risk_reserve_cents,
    )
