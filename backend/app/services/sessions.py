"""Start, extend, and end sessions. Money is copied from the price tables at start."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.enums import BillingMode, PaymentMethod, SessionStatus, StationStatus
from app.models.identity import User
from app.models.play_session import Payment, PlaySession, SessionExtension
from app.models.pricing import Package, PricingPlan
from app.models.station import Station
from app.schemas.money import rupees, rupees_text
from app.services.access import record_audit
from app.services.billing import (
    charge_rupees,
    extension_seconds,
    overtime_seconds,
    postpaid_billable_seconds,
    prepaid_purchase_seconds,
)

ZERO = Decimal("0.00")


class SessionError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def start_session(
    db: Session,
    *,
    station_code: str,
    staff: User,
    billing_mode: BillingMode,
    customer_id: str | None = None,
    guest_label: str | None = None,
    package_code: str | None = None,
    duration_seconds: int | None = None,
    payment_method: PaymentMethod | None = None,
    reservation_id: str | None = None,
    now: datetime | None = None,
) -> PlaySession:
    from app.services.reservations import ReservationError, claim_for_start, mark_started

    started_at = _utc(now)
    station = _available_station(db, station_code)
    try:
        reservation = claim_for_start(db, station=station, reservation_id=reservation_id, started_at=started_at)
    except ReservationError as exc:
        raise SessionError(exc.status_code, exc.detail) from exc
    customer = _customer(db, customer_id) if customer_id else None
    label = guest_label.strip() if guest_label else None
    if customer is None and not label:
        raise SessionError(422, "Choose a customer or enter a guest name")
    plan = _plan_for(db, station)
    package = _package_for(db, station, package_code) if package_code else None
    purchased, due_now = _opening_quote(billing_mode, plan, package, duration_seconds)
    if due_now > 0 and payment_method not in {PaymentMethod.CASH, PaymentMethod.UPI, PaymentMethod.CARD}:
        raise SessionError(422, "Choose cash, UPI, or card for the amount due now")

    claimed = db.execute(
        update(Station)
        .where(Station.id == station.id, Station.status == StationStatus.AVAILABLE)
        .values(status=StationStatus.IN_SESSION)
    )
    if claimed.rowcount != 1:
        raise SessionError(409, "Station is not available")

    snapshot = {
        "hourly_rate_rupees": rupees_text(plan.hourly_rate_rupees),
        "billing_increment_seconds": plan.billing_increment_seconds,
        "minimum_duration_seconds": plan.minimum_duration_seconds,
        "package_code": None if package is None else package.code,
        "package_price_rupees": None if package is None else rupees_text(package.price_rupees),
        "purchased_seconds": purchased,
        "billing_mode": billing_mode.value,
    }
    play = PlaySession(
        station_id=station.id,
        customer_id=None if customer is None else customer.id,
        guest_label=label,
        staff_user_id=staff.id,
        status=SessionStatus.ACTIVE,
        billing_mode=billing_mode,
        started_at=started_at,
        scheduled_end_at=None if purchased == 0 else started_at + timedelta(seconds=purchased),
        hourly_rate_rupees=rupees(plan.hourly_rate_rupees),
        billing_increment_seconds=plan.billing_increment_seconds,
        minimum_duration_seconds=plan.minimum_duration_seconds,
        purchased_seconds=purchased,
        package_code=None if package is None else package.code,
        package_price_rupees=None if package is None else rupees(package.price_rupees),
        pricing_snapshot=snapshot,
    )
    db.add(play)
    try:
        db.flush()
        if reservation is not None:
            mark_started(reservation, play.id)
        if due_now > 0 and payment_method is not None:
            _record_payment(db, play, due_now, payment_method, staff, started_at)
        elif billing_mode == BillingMode.FREE_PLAY:
            _record_payment(db, play, ZERO, PaymentMethod.FREE, staff, started_at)
        record_audit(
            db,
            actor=staff,
            action="session.started",
            entity_type="session",
            entity_id=str(play.id),
            detail=f"station={station.code}; mode={billing_mode.value}; due={rupees_text(due_now)}",
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise SessionError(409, "That station or customer already has an active session") from exc
    db.refresh(play)
    return play


def extend_session(
    db: Session,
    *,
    session_id: str,
    staff: User,
    duration_seconds: int,
    payment_method: PaymentMethod | None = None,
    now: datetime | None = None,
) -> PlaySession:
    moment = _utc(now)
    play = _active(db, session_id)
    added = extension_seconds(duration_seconds, play.billing_increment_seconds)
    amount = ZERO if play.billing_mode == BillingMode.POSTPAID or play.billing_mode == BillingMode.FREE_PLAY else charge_rupees(play.hourly_rate_rupees, added)
    if amount > 0 and payment_method not in {PaymentMethod.CASH, PaymentMethod.UPI, PaymentMethod.CARD}:
        raise SessionError(422, "Choose cash, UPI, or card for the extension")
    if play.billing_mode == BillingMode.PREPAID:
        play.purchased_seconds += added
        base = play.started_at
        play.scheduled_end_at = base + timedelta(seconds=play.purchased_seconds)
    else:
        anchor = play.scheduled_end_at or moment
        play.scheduled_end_at = anchor + timedelta(seconds=added)
    db.add(
        SessionExtension(
            session_id=play.id,
            added_seconds=added,
            amount_rupees=amount,
            staff_user_id=staff.id,
            created_at=moment,
        )
    )
    if amount > 0 and payment_method is not None:
        _record_payment(db, play, amount, payment_method, staff, moment)
    record_audit(
        db,
        actor=staff,
        action="session.extended",
        entity_type="session",
        entity_id=str(play.id),
        detail=f"added_seconds={added}; amount={rupees_text(amount)}",
    )
    db.commit()
    db.refresh(play)
    return play


def end_session(
    db: Session,
    *,
    session_id: str,
    staff: User,
    payment_method: PaymentMethod | None = None,
    now: datetime | None = None,
) -> PlaySession:
    ended_at = _utc(now)
    play = _active(db, session_id)
    if ended_at < play.started_at:
        raise SessionError(422, "End time is before the session start")
    final_amount = amount_due_at(play, ended_at)
    paid = _paid(db, play.id)
    balance = rupees(final_amount - paid)
    if balance < 0:
        balance = ZERO
    if balance > 0 and payment_method not in {PaymentMethod.CASH, PaymentMethod.UPI, PaymentMethod.CARD}:
        raise SessionError(422, "Choose cash, UPI, or card for the remaining amount")
    play.status = SessionStatus.ENDED
    play.ended_at = ended_at
    play.final_amount_rupees = final_amount
    if balance > 0 and payment_method is not None:
        _record_payment(db, play, balance, payment_method, staff, ended_at)
    db.execute(
        update(Station)
        .where(Station.id == play.station_id, Station.status == StationStatus.IN_SESSION)
        .values(status=StationStatus.AVAILABLE)
    )
    record_audit(
        db,
        actor=staff,
        action="session.ended",
        entity_type="session",
        entity_id=str(play.id),
        detail=f"final={rupees_text(final_amount)}; balance={rupees_text(balance)}",
    )
    db.commit()
    db.refresh(play)
    return play


def amount_due_at(play: PlaySession, ended_at: datetime) -> Decimal:
    elapsed = int((ended_at - play.started_at).total_seconds())
    if play.billing_mode == BillingMode.FREE_PLAY:
        return ZERO
    if play.billing_mode == BillingMode.POSTPAID and play.package_price_rupees is None:
        seconds = postpaid_billable_seconds(elapsed, play.billing_increment_seconds, play.minimum_duration_seconds)
        return charge_rupees(play.hourly_rate_rupees, seconds)
    base = play.package_price_rupees if play.package_price_rupees is not None else charge_rupees(play.hourly_rate_rupees, play.purchased_seconds)
    extra = overtime_seconds(elapsed, play.purchased_seconds, play.billing_increment_seconds)
    return rupees(base + charge_rupees(play.hourly_rate_rupees, extra))


def _opening_quote(mode: BillingMode, plan: PricingPlan, package: Package | None, duration_seconds: int | None) -> tuple[int, Decimal]:
    if mode == BillingMode.FREE_PLAY:
        if package is not None:
            raise SessionError(422, "Free play does not use a package")
        return 0, ZERO
    if package is not None and mode == BillingMode.PREPAID:
        return package.duration_seconds, rupees(package.price_rupees)
    if package is not None and mode == BillingMode.POSTPAID:
        return package.duration_seconds, ZERO
    if mode == BillingMode.PREPAID:
        if duration_seconds is None:
            raise SessionError(422, "Prepaid hourly play needs a duration")
        purchased = prepaid_purchase_seconds(duration_seconds, plan.billing_increment_seconds, plan.minimum_duration_seconds)
        return purchased, charge_rupees(plan.hourly_rate_rupees, purchased)
    return 0, ZERO


def _available_station(db: Session, code: str) -> Station:
    station = db.scalar(select(Station).where(Station.code == code))
    if station is None:
        raise SessionError(404, "Station not found")
    if not station.is_customer_station or not station.is_billable:
        raise SessionError(422, "This station cannot be billed")
    if station.status != StationStatus.AVAILABLE:
        raise SessionError(409, "Station is not available")
    return station


def _plan_for(db: Session, station: Station) -> PricingPlan:
    override = db.scalar(
        select(PricingPlan).where(PricingPlan.station_id == station.id, PricingPlan.is_active.is_(True))
    )
    if override is not None:
        return override
    plan = db.scalar(
        select(PricingPlan).where(
            PricingPlan.device_type == station.device_type,
            PricingPlan.station_id.is_(None),
            PricingPlan.is_active.is_(True),
        )
    )
    if plan is None:
        raise SessionError(422, "No price is configured for this station")
    return plan


def _package_for(db: Session, station: Station, code: str) -> Package:
    package = db.scalar(select(Package).where(Package.code == code, Package.is_active.is_(True)))
    if package is None:
        raise SessionError(404, "Package not found")
    if package.device_type != station.device_type:
        raise SessionError(422, "That package is for a different device")
    return package


def _customer(db: Session, customer_id: str) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None or not customer.is_active:
        raise SessionError(404, "Customer not found")
    return customer


def _active(db: Session, session_id: str) -> PlaySession:
    play = db.get(PlaySession, session_id)
    if play is None:
        raise SessionError(404, "Session not found")
    if play.status != SessionStatus.ACTIVE:
        raise SessionError(409, "Session is already closed")
    return play


def _paid(db: Session, session_id) -> Decimal:
    amounts = db.scalars(select(Payment.amount_rupees).where(Payment.session_id == session_id))
    return rupees(sum(amounts, ZERO))


def _record_payment(db: Session, play: PlaySession, amount: Decimal, method: PaymentMethod, staff: User, moment: datetime) -> None:
    db.add(
        Payment(
            session_id=play.id,
            amount_rupees=rupees(amount),
            method=method,
            staff_user_id=staff.id,
            recorded_at=moment,
        )
    )


def _utc(moment: datetime | None) -> datetime:
    current = moment or datetime.now(timezone.utc)
    if current.tzinfo is None:
        return current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)
