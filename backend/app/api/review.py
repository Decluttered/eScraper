import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.listing import ListingObservationModel, RawListingModel
from app.db.session import get_session
from app.domain.enums import Condition

router = APIRouter(prefix="/review", tags=["review"])


class ReviewResolveRequest(BaseModel):
    product_id: uuid.UUID
    condition: Condition
    confirmed_flags: list[str] = []

    model_config = ConfigDict(extra="forbid")


@router.post("/{observation_id}/resolve")
async def resolve_review(
    observation_id: uuid.UUID,
    request: ReviewResolveRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    observation = await session.scalar(
        select(ListingObservationModel).where(
            ListingObservationModel.id == observation_id
        )
    )
    if observation is None:
        raise HTTPException(status_code=404, detail="observation not found")
    observation.product_id = request.product_id
    observation.condition = request.condition
    observation.flags = sorted(set(request.confirmed_flags))
    observation.review_status = "RESOLVED"
    observation.model_match_confidence_bps = 10000

    raw = await session.scalar(
        select(RawListingModel).where(RawListingModel.id == observation.raw_listing_id)
    )
    if raw is not None:
        existing_corrections = list(raw.raw_metadata.get("corrections", []))
        existing_corrections.append(
            {
                "observation_id": str(observation_id),
                "product_id": str(request.product_id),
                "condition": request.condition.value,
            }
        )
        raw.raw_metadata = {**raw.raw_metadata, "corrections": existing_corrections}

    await session.commit()
    return {"status": "resolved"}
