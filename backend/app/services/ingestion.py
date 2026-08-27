import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.listing import ListingObservationModel, RawListingModel
from app.domain.enums import Condition
from app.schemas.sources import IngestionResult, SourceEnvelope


def payload_checksum(envelope: SourceEnvelope) -> str:
    payload = envelope.model_dump(mode="json", exclude={"captured_at"})
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


class IngestionService:
    async def ingest(
        self, session: AsyncSession, envelope: SourceEnvelope
    ) -> IngestionResult:
        checksum = payload_checksum(envelope)
        existing = await session.scalar(
            select(RawListingModel).where(
                RawListingModel.source == envelope.source,
                RawListingModel.external_id == envelope.external_id,
                RawListingModel.payload_checksum == checksum,
            )
        )
        if existing is not None:
            observation = await session.scalar(
                select(ListingObservationModel).where(
                    ListingObservationModel.raw_listing_id == existing.id
                )
            )
            if observation is None:
                raise RuntimeError("raw listing exists without observation")
            return IngestionResult(
                raw_listing_id=existing.id,
                observation_id=observation.id,
                created=False,
            )

        raw = RawListingModel(
            source=envelope.source,
            external_id=envelope.external_id,
            source_url=str(envelope.source_url),
            captured_at=envelope.captured_at,
            raw_title=envelope.title,
            raw_description=envelope.description,
            asking_price_cents=envelope.asking_price_cents,
            shipping_cents=envelope.shipping_cents,
            raw_condition=envelope.condition,
            location_summary=envelope.location_summary,
            payload_checksum=checksum,
            import_method=envelope.import_method,
            raw_metadata=envelope.metadata,
        )
        session.add(raw)
        await session.flush()
        observation = ListingObservationModel(
            raw_listing_id=raw.id,
            product_id=None,
            asking_price_cents=envelope.asking_price_cents,
            shipping_cents=envelope.shipping_cents,
            condition=Condition.UNKNOWN,
            sale_format=envelope.sale_format,
            model_match_confidence_bps=0,
            flags=[],
            review_status="PENDING",
        )
        session.add(observation)
        await session.commit()
        return IngestionResult(
            raw_listing_id=raw.id,
            observation_id=observation.id,
            created=True,
        )
