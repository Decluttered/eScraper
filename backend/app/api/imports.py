from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.market import MarketComparableModel
from app.db.session import get_session
from app.schemas.comparables import ComparableImportRow
from app.schemas.deals import (
    CompanionImportRequest,
    ComparableCommitRequest,
    ComparableCommitResponse,
    ComparablePreviewRequest,
    ComparablePreviewResponse,
)
from app.schemas.sources import IngestionResult, SourceEnvelope
from app.services.ingestion import IngestionService
from app.services.text_sanitize import sanitize_import_text
from app.sources.imports import hash_comparable_rows, parse_comparable_csv

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/listings", response_model=IngestionResult)
async def import_listing(
    payload: CompanionImportRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> IngestionResult:
    envelope = SourceEnvelope(
        source=payload.source,
        external_id=payload.external_id,
        source_url=payload.source_url,
        captured_at=payload.captured_at,
        title=sanitize_import_text(payload.title),
        description=sanitize_import_text(payload.description),
        asking_price_cents=payload.asking_price_cents,
        shipping_cents=payload.shipping_cents,
        condition=payload.condition,
        location_summary=payload.location_summary,
        sale_format=payload.sale_format,
        metadata={},
        import_method=payload.import_method,
    )
    result = await IngestionService().ingest(session, envelope)
    response.status_code = 201 if result.created else 200
    return result


@router.post("/comparables/preview", response_model=ComparablePreviewResponse)
async def preview_comparables(payload: ComparablePreviewRequest) -> ComparablePreviewResponse:
    rows, errors = parse_comparable_csv(payload.csv_content)
    row_dicts = [row.model_dump(mode="json") for row in rows]
    return ComparablePreviewResponse(
        preview_token=hash_comparable_rows(row_dicts),
        rows=row_dicts,
        errors=[error.model_dump(mode="json") for error in errors],
    )


@router.post("/comparables/commit", response_model=ComparableCommitResponse)
async def commit_comparables(
    payload: ComparableCommitRequest,
    session: AsyncSession = Depends(get_session),
) -> ComparableCommitResponse:
    if hash_comparable_rows(payload.rows) != payload.preview_token:
        raise HTTPException(status_code=409, detail="preview rows have changed since preview")

    validated = [ComparableImportRow.model_validate(row) for row in payload.rows]
    session.add_all(
        MarketComparableModel(
            product_id=row.product_id,
            source=row.source,
            status=row.status,
            condition=row.condition,
            item_price_cents=row.item_price_cents,
            shipping_cents=row.shipping_cents,
            occurred_at=row.occurred_at,
            variant_match_confidence_bps=row.variant_match_confidence_bps,
            source_quality="CSV_IMPORT",
            observation_count=row.observation_count,
            sold_through_bps=row.sold_through_bps,
            source_note=row.source_note,
        )
        for row in validated
    )
    await session.commit()
    return ComparableCommitResponse(created_count=len(validated))
