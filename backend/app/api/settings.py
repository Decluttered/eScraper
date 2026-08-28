from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.market import CostProfileModel, RiskRuleModel
from app.db.session import get_session
from app.schemas.operations import (
    CostProfileCreate,
    CostProfileOut,
    CredentialStatus,
    RiskRuleCreate,
    RiskRuleOut,
    SettingsOut,
)

router = APIRouter(prefix="/settings", tags=["settings"])


def _credential_status(value: str | None) -> CredentialStatus:
    if value is None:
        return CredentialStatus.MISSING
    return CredentialStatus.SET if value.strip() else CredentialStatus.EMPTY


async def _effective_profiles(session: AsyncSession, now: datetime) -> list[CostProfileModel]:
    rows = (
        await session.scalars(
            select(CostProfileModel).where(
                CostProfileModel.effective_from <= now,
            )
        )
    ).all()
    return [row for row in rows if row.effective_to is None or row.effective_to > now]


async def _effective_rules(session: AsyncSession, now: datetime) -> list[RiskRuleModel]:
    rows = (
        await session.scalars(
            select(RiskRuleModel).where(
                RiskRuleModel.effective_from <= now,
            )
        )
    ).all()
    return [row for row in rows if row.effective_to is None or row.effective_to > now]


@router.get("", response_model=SettingsOut)
async def get_settings_overview(session: AsyncSession = Depends(get_session)) -> SettingsOut:
    settings = get_settings()
    now = datetime.now(UTC)
    profiles = await _effective_profiles(session, now)
    rules = await _effective_rules(session, now)
    return SettingsOut(
        ebay_client_id=_credential_status(
            settings.ebay_client_id.get_secret_value() if settings.ebay_client_id else None
        ),
        ebay_client_secret=_credential_status(
            settings.ebay_client_secret.get_secret_value()
            if settings.ebay_client_secret
            else None
        ),
        ebay_marketplace_id=settings.ebay_marketplace_id,
        cost_profiles=list(profiles),
        risk_rules=list(rules),
    )


@router.post("/cost-profiles", response_model=CostProfileOut, status_code=201)
async def create_cost_profile(
    payload: CostProfileCreate, session: AsyncSession = Depends(get_session)
) -> CostProfileModel:
    current_max = await session.scalar(
        select(func.max(CostProfileModel.version)).where(
            CostProfileModel.name == payload.name
        )
    )
    profile = CostProfileModel(
        name=payload.name,
        version=(current_max or 0) + 1,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        tax_profile=payload.tax_profile,
        configuration=payload.configuration,
    )
    session.add(profile)
    await session.commit()
    return profile


@router.post("/risk-rules", response_model=RiskRuleOut, status_code=201)
async def create_risk_rule(
    payload: RiskRuleCreate, session: AsyncSession = Depends(get_session)
) -> RiskRuleModel:
    current_max = await session.scalar(
        select(func.max(RiskRuleModel.version)).where(RiskRuleModel.key == payload.key)
    )
    rule = RiskRuleModel(
        key=payload.key,
        version=(current_max or 0) + 1,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        matcher=payload.matcher,
        severity=payload.severity,
        required_evidence=payload.required_evidence,
        reserve_adjustment_bps=payload.reserve_adjustment_bps,
        recommendation_cap=payload.recommendation_cap,
        explanation=payload.explanation,
    )
    session.add(rule)
    await session.commit()
    return rule
