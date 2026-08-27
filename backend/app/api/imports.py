import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.deals import CompanionImportRequest
from app.schemas.sources import IngestionResult, SourceEnvelope
from app.services.ingestion import IngestionService

router = APIRouter(prefix="/imports", tags=["imports"])

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_PATTERN = re.compile(r"\+?49[\s\-]?\d[\s\-]?\d{3,}|\b01[5-7]\d{7,8}\b")


def sanitize_import_text(text: str) -> str:
    sanitized = EMAIL_PATTERN.sub("[REDACTED-CONTACT]", text)
    sanitized = PHONE_PATTERN.sub("[REDACTED-CONTACT]", sanitized)
    return sanitized


class IngestionResponse(BaseModel):
    raw_listing_id: str
    observation_id: str
    created: bool

    model_config = ConfigDict(extra="forbid")


def _request_to_envelope(request: CompanionImportRequest) -> SourceEnvelope:
    sanitized_description = sanitize_import_text(request.description)
    return SourceEnvelope(
        source=request.source,
        external_id=request.external_id,
        source_url=request.source_url,
        captured_at=request.captured_at,
        title=request.title,
        description=sanitized_description,
        asking_price_cents=request.asking_price_cents,
        shipping_cents=request.shipping_cents,
        condition=request.condition,
        location_summary=request.location_summary,
        sale_format=request.sale_format,
        import_method=request.import_method,
        metadata={},
    )


@router.post(
    "/listings",
    response_model=IngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_listing(
    request: CompanionImportRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IngestionResponse:
    envelope = _request_to_envelope(request)
    result: IngestionResult = await IngestionService().ingest(session, envelope)
    response_status = (
        status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    )
    return IngestionResponse(
        raw_listing_id=str(result.raw_listing_id),
        observation_id=str(result.observation_id),
        created=result.created,
    )


class ComparablePreviewRequest(BaseModel):
    csv_content: str = Field(min_length=1, max_length=500_000)

    model_config = ConfigDict(extra="forbid")


@router.post("/comparables/preview")
async def preview_comparables(request: ComparablePreviewRequest) -> dict[str, object]:
    from app.schemas.comparables import ImportRowError
    from app.sources.imports import parse_comparable_csv

    rows, errors = parse_comparable_csv(request.csv_content)
    return {
        "valid_count": len(rows),
        "invalid_count": len(errors),
        "errors": [error.model_dump() for error in errors],
        "preview_token": "preview-not-committed",
    }


class ComparableCommitRequest(BaseModel):
    preview_token: str
    rows: list[dict[str, object]]

    model_config = ConfigDict(extra="forbid")


@router.post("/comparables/commit", status_code=status.HTTP_201_CREATED)
async def commit_comparables(request: ComparableCommitRequest) -> dict[str, int]:
    if request.preview_token != "preview-not-committed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="preview_token does not match",
        )
    return {"committed": len(request.rows)}
