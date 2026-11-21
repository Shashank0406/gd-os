import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.models.pricing import Package, PriceChangeLog, PricingPlan, PricingSchedule
from app.schemas.catalog import CatalogOut, PricingPlanOut
from app.schemas.money import rupees, rupees_text
from app.services.access import record_audit

router = APIRouter(tags=["pricing"])


class PlanPriceIn(BaseModel):
    hourly_rate_rupees: Decimal

    @field_validator("hourly_rate_rupees")
    @classmethod
    def within_range(cls, value: Decimal) -> Decimal:
        amount = rupees(value)
        if amount < 0 or amount > Decimal("1000000.00"):
            raise ValueError("Hourly rate must be from 0.00 to 1000000.00 rupees")
        return amount


@router.get("/pricing", response_model=CatalogOut)
def get_pricing(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("pricing.read")),
) -> CatalogOut:
    plans = list(db.scalars(select(PricingPlan).order_by(PricingPlan.device_type, PricingPlan.name)))
    packages = list(db.scalars(select(Package).order_by(Package.sort_order, Package.code)))
    schedule_count = db.scalar(select(func.count()).select_from(PricingSchedule)) or 0
    return CatalogOut(plans=plans, packages=packages, schedule_count=schedule_count)


@router.patch("/pricing/plans/{plan_id}", response_model=PricingPlanOut)
def update_plan_price(
    plan_id: uuid.UUID,
    body: PlanPriceIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("pricing.write")),
) -> PricingPlan:
    plan = db.get(PricingPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Pricing plan not found")
    old = rupees(plan.hourly_rate_rupees)
    new = body.hourly_rate_rupees
    if old != new:
        plan.hourly_rate_rupees = new
        db.add(
            PriceChangeLog(
                entity_type="pricing_plan",
                entity_id=plan.id,
                field_name="hourly_rate_rupees",
                old_value=rupees_text(old),
                new_value=rupees_text(new),
                actor_label=actor.username,
                note="price updated",
            )
        )
        record_audit(
            db,
            actor=actor,
            action="pricing.updated",
            entity_type="pricing_plan",
            entity_id=str(plan.id),
            detail=f"{plan.name}: {rupees_text(old)} -> {rupees_text(new)}",
        )
        db.commit()
        db.refresh(plan)
    return plan
