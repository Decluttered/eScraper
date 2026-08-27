from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.market import CostProfileModel, RiskRuleModel
from app.db.session import get_session
from app.schemas.operations import CredentialStatus

router = APIRouter(prefix="/settings", tags=["settings"])


def _credential_status(value: object) -> str:
    if value is None:
        return CredentialStatus.MISSING
    if not isinstance(value, str) or value == "":
        return CredentialStatus.EMPTY
    return CredentialStatus.SET


@router.get("")
async def get_settings_view(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    settings = get_settings()
    cost_profiles = (await session.scalars(select(CostProfileModel))).all()
    risk_rules = (await session.scalars(select(RiskRuleModel))).all()
    return {
        "ebay_client_id": _credential_status(getattr(settings, "ebay_client_id", None)),
        "ebay_client_secret": _credential_status(
            getattr(settings, "ebay_client_secret", None)
        ),
        "ebay_marketplace_id": getattr(settings, "ebay_marketplace_id", "EBAY_DE"),
        "cost_profiles": [
            {
                "id": str(p.id),
                "name": p.name,
                "version": p.version,
                "tax_profile": p.tax_profile.value,
            }
            for p in cost_profiles
        ],
        "risk_rules": [
            {
                "id": str(r.id),
                "key": r.key,
                "version": r.version,
                "severity": r.severity,
            }
            for r in risk_rules
        ],
    }
