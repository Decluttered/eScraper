from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.listing import ListingObservationModel, RawListingModel
from app.db.session import get_session
from app.schemas.deals import ReviewResolutionRequest, ReviewResolutionResponse

router = APIRouter(prefix="/review", tags=["review"])


@router.post("/{observation_id}/resolve", response_model=ReviewResolutionResponse)
async def resolve_review(
    observation_id: UUID,
    payload: ReviewResolutionRequest,
    session: AsyncSession = Depends(get_session),
) -> ReviewResolutionResponse:
    observation = await session.get(ListingObservationModel, observation_id)
    if observation is None:
        raise HTTPException(status_code=404, detail="observation not found")

    observation.product_id = payload.product_id
    observation.condition = payload.condition
    observation.flags = payload.confirmed_flags
    observation.review_status = "RESOLVED"
    observation.model_match_confidence_bps = 10000

    raw_listing = await session.get(RawListingModel, observation.raw_listing_id)
    if raw_listing is not None:
        metadata = dict(raw_listing.raw_metadata)
        corrections = list(metadata.get("corrections", []))
        corrections.append(
            {
                "at": datetime.now(UTC).isoformat(),
                "product_id": str(payload.product_id),
                "condition": payload.condition.value,
                "confirmed_flags": payload.confirmed_flags,
            }
        )
        metadata["corrections"] = corrections
        raw_listing.raw_metadata = metadata

    await session.commit()
    return ReviewResolutionResponse(
        observation_id=observation.id,
        product_id=observation.product_id,
        condition=observation.condition,
        flags=observation.flags,
        review_status=observation.review_status,
    )
