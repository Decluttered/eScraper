from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.operations import AlertModel
from app.db.session import get_session
from app.schemas.operations import AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
async def list_unacknowledged_alerts(
    session: AsyncSession = Depends(get_session),
) -> list[AlertModel]:
    rows = (
        await session.scalars(
            select(AlertModel)
            .where(AlertModel.acknowledged_at.is_(None))
            .order_by(AlertModel.created_at.desc())
        )
    ).all()
    return list(rows)


@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
async def acknowledge_alert(
    alert_id: UUID, session: AsyncSession = Depends(get_session)
) -> AlertModel:
    alert = await session.get(AlertModel, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")
    alert.acknowledged_at = datetime.now(UTC)
    await session.commit()
    return alert
