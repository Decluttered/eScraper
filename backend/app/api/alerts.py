import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.operations import AlertModel
from app.db.session import get_session

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[dict])
async def list_unacknowledged_alerts(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict]:
    alerts = (
        await session.scalars(
            select(AlertModel).where(AlertModel.acknowledged_at.is_(None))
        )
    ).all()
    return [
        {
            "id": str(a.id),
            "evaluation_id": str(a.evaluation_id),
            "alert_type": a.alert_type,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]


@router.post("/{alert_id}/acknowledge", status_code=200)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    alert = await session.scalar(
        select(AlertModel).where(AlertModel.id == alert_id)
    )
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")
    alert.acknowledged_at = datetime.now(UTC)
    await session.commit()
    return {"status": "acknowledged"}
