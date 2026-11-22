"""Peak and off-peak rates. A schedule changes new sessions only."""

from datetime import datetime, time, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import User
from app.models.pricing import PriceChangeLog, PricingPlan, PricingSchedule
from app.schemas.money import rupees, rupees_text
from app.services.access import record_audit

KOLKATA = ZoneInfo("Asia/Kolkata")


class PricingError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def hourly_rate_at(db: Session, plan: PricingPlan, moment: datetime) -> tuple[Decimal, str | None]:
    local = _local(moment)
    matches = [
        schedule
        for schedule in _active_schedules(db, plan.id)
        if _covers(schedule, local.isoweekday(), local.timetz().replace(tzinfo=None))
    ]
    if len(matches) > 1:
        raise PricingError(409, "More than one rate applies now")
    if len(matches) == 1:
        return rupees(matches[0].hourly_rate_rupees), matches[0].label
    return rupees(plan.hourly_rate_rupees), None


def create_schedule(
    db: Session,
    *,
    plan_id: str,
    label: str,
    days_of_week: list[int],
    start_local_time: time,
    end_local_time: time,
    hourly_rate_rupees: Decimal,
    staff: User,
) -> PricingSchedule:
    plan = db.get(PricingPlan, plan_id)
    if plan is None or not plan.is_active:
        raise PricingError(404, "Pricing plan not found")
    name = label.strip()
    if not name or len(name) > 80:
        raise PricingError(422, "Enter a schedule name")
    days = _days(days_of_week)
    if start_local_time >= end_local_time:
        raise PricingError(422, "The end time must be after the start time")
    rate = rupees(hourly_rate_rupees)
    if rate < 0 or rate > Decimal("1000000.00"):
        raise PricingError(422, "Hourly rate must be from 0.00 to 1000000.00 rupees")
    for existing in _active_schedules(db, plan.id):
        if _ranges_overlap(existing, days, start_local_time, end_local_time):
            raise PricingError(409, "That schedule overlaps another rate")
    schedule = PricingSchedule(
        pricing_plan_id=plan.id,
        label=name,
        days_of_week=",".join(str(day) for day in days),
        start_local_time=start_local_time,
        end_local_time=end_local_time,
        hourly_rate_rupees=rate,
        is_active=True,
    )
    db.add(schedule)
    db.flush()
    db.add(
        PriceChangeLog(
            entity_type="pricing_schedule",
            entity_id=schedule.id,
            field_name="hourly_rate_rupees",
            old_value=None,
            new_value=rupees_text(rate),
            actor_label=staff.username,
            note=name,
        )
    )
    record_audit(
        db,
        actor=staff,
        action="pricing.schedule_created",
        entity_type="pricing_schedule",
        entity_id=str(schedule.id),
        detail=f"{plan.name}; {name}; {rupees_text(rate)}; days={schedule.days_of_week}",
    )
    db.commit()
    db.refresh(schedule)
    return schedule


def deactivate_schedule(db: Session, *, schedule_id: str, staff: User) -> PricingSchedule:
    schedule = db.get(PricingSchedule, schedule_id)
    if schedule is None:
        raise PricingError(404, "Schedule not found")
    if schedule.is_active:
        schedule.is_active = False
        record_audit(
            db,
            actor=staff,
            action="pricing.schedule_deactivated",
            entity_type="pricing_schedule",
            entity_id=str(schedule.id),
            detail=schedule.label,
        )
        db.commit()
        db.refresh(schedule)
    return schedule


def _active_schedules(db: Session, plan_id) -> list[PricingSchedule]:
    return list(
        db.scalars(
            select(PricingSchedule).where(
                PricingSchedule.pricing_plan_id == plan_id,
                PricingSchedule.is_active.is_(True),
            )
        )
    )


def _covers(schedule: PricingSchedule, weekday: int, local_time: time) -> bool:
    days = {int(part) for part in schedule.days_of_week.split(",") if part}
    if weekday not in days:
        return False
    clock = local_time.replace(microsecond=0)
    return schedule.start_local_time <= clock < schedule.end_local_time


def _ranges_overlap(existing: PricingSchedule, days: list[int], start: time, end: time) -> bool:
    existing_days = {int(part) for part in existing.days_of_week.split(",") if part}
    if existing_days.isdisjoint(days):
        return False
    return start < existing.end_local_time and existing.start_local_time < end


def _days(days_of_week: list[int]) -> list[int]:
    if not days_of_week:
        raise PricingError(422, "Choose at least one day")
    days = sorted(set(days_of_week))
    if any(day < 1 or day > 7 for day in days):
        raise PricingError(422, "Days are Monday 1 through Sunday 7")
    stored = ",".join(str(day) for day in days)
    if len(stored) > 32:
        raise PricingError(422, "Choose fewer days")
    return days


def _local(moment: datetime) -> datetime:
    current = moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)
    return current.astimezone(KOLKATA)
