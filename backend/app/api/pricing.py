import uuid
from datetime import datetime, time, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.models.pricing import Package, PriceChangeLog, PricingPlan, PricingSchedule
from app.schemas.catalog import CatalogOut, PricingPlanOut, ScheduleOut
from app.schemas.money import rupees, rupees_text
from app.services.access import record_audit
from app.services.pricing import PricingError, create_schedule, deactivate_schedule, hourly_rate_at

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


class ScheduleIn(BaseModel):
    label: str
    days_of_week: list[int]
    start_local_time: time
    end_local_time: time
    hourly_rate_rupees: Decimal


def _call(action):
    try:
        return action()
    except PricingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _schedule_out(schedule: PricingSchedule) -> ScheduleOut:
    return ScheduleOut(
        id=schedule.id,
        pricing_plan_id=schedule.pricing_plan_id,
        label=schedule.label,
        days_of_week=schedule.days_of_week,
        start_local_time=schedule.start_local_time.strftime("%H:%M"),
        end_local_time=schedule.end_local_time.strftime("%H:%M"),
        hourly_rate_rupees=rupees_text(schedule.hourly_rate_rupees),
        is_active=schedule.is_active,
    )


@router.get("/pricing", response_model=CatalogOut)
def get_pricing(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("pricing.read")),
) -> CatalogOut:
    plans = list(db.scalars(select(PricingPlan).order_by(PricingPlan.device_type, PricingPlan.name)))
    packages = list(db.scalars(select(Package).order_by(Package.sort_order, Package.code)))
    schedules = list(
        db.scalars(
            select(PricingSchedule)
            .where(PricingSchedule.is_active.is_(True))
            .order_by(PricingSchedule.start_local_time, PricingSchedule.label)
        )
    )
    now = datetime.now(timezone.utc)
    priced: list[PricingPlanOut] = []
    for plan in plans:
        item = PricingPlanOut.model_validate(plan)
        try:
            rate, label = hourly_rate_at(db, plan, now)
        except PricingError:
            rate, label = rupees(plan.hourly_rate_rupees), None
        priced.append(item.model_copy(update={"effective_hourly_rate_rupees": rate, "effective_label": label}))
    return CatalogOut(
        plans=priced,
        packages=packages,
        schedules=[_schedule_out(schedule) for schedule in schedules],
        schedule_count=len(schedules),
    )


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


@router.post("/pricing/plans/{plan_id}/schedules", response_model=ScheduleOut, status_code=201)
def add_schedule(
    plan_id: uuid.UUID,
    body: ScheduleIn,
    db: Session = Depends(get_db),
    staff: User = Depends(require_permission("pricing.write")),
) -> ScheduleOut:
    schedule = _call(
        lambda: create_schedule(
            db,
            plan_id=str(plan_id),
            label=body.label,
            days_of_week=body.days_of_week,
            start_local_time=body.start_local_time,
            end_local_time=body.end_local_time,
            hourly_rate_rupees=body.hourly_rate_rupees,
            staff=staff,
        )
    )
    return _schedule_out(schedule)


@router.post("/pricing/schedules/{schedule_id}/deactivate", response_model=ScheduleOut)
def retire_schedule(
    schedule_id: uuid.UUID,
    db: Session = Depends(get_db),
    staff: User = Depends(require_permission("pricing.write")),
) -> ScheduleOut:
    schedule = _call(lambda: deactivate_schedule(db, schedule_id=str(schedule_id), staff=staff))
    return _schedule_out(schedule)
