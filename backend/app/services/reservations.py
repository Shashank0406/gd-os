"""Hold a station for a guest. Overlapping holds on the same station are rejected."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.enums import ReservationStatus, StationStatus
from app.models.identity import User
from app.models.reservation import Reservation
from app.models.station import Station
from app.services.access import record_audit

MIN_SECONDS = 30 * 60
MAX_SECONDS = 12 * 60 * 60


class ReservationError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def book_reservation(
    db: Session,
    *,
    station_code: str,
    staff: User,
    starts_at: datetime,
    duration_seconds: int,
    customer_id: str | None = None,
    guest_label: str | None = None,
    now: datetime | None = None,
) -> Reservation:
    start = _utc(starts_at)
    moment = _utc(now)
    if duration_seconds < MIN_SECONDS or duration_seconds > MAX_SECONDS:
        raise ReservationError(422, "A reservation must be from 30 minutes to 12 hours")
    if start < moment - timedelta(minutes=1):
        raise ReservationError(422, "Reservation starts in the past")
    end = start + timedelta(seconds=duration_seconds)
    station = _station(db, station_code)
    customer = _customer(db, customer_id) if customer_id else None
    label = guest_label.strip() if guest_label else None
    if customer is None and not label:
        raise ReservationError(422, "Choose a customer or enter a guest name")
    _reject_overlap(db, station, start, end)
    reservation = Reservation(
        station_id=station.id,
        customer_id=None if customer is None else customer.id,
        guest_label=label,
        staff_user_id=staff.id,
        status=ReservationStatus.SCHEDULED,
        starts_at=start,
        ends_at=end,
    )
    db.add(reservation)
    try:
        db.flush()
        record_audit(
            db,
            actor=staff,
            action="reservation.created",
            entity_type="reservation",
            entity_id=str(reservation.id),
            detail=f"station={station.code}; start={start.isoformat()}",
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ReservationError(409, "That station is already reserved then") from exc
    db.refresh(reservation)
    return reservation


def cancel_reservation(db: Session, *, reservation_id: str, staff: User) -> Reservation:
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise ReservationError(404, "Reservation not found")
    if reservation.status != ReservationStatus.SCHEDULED:
        raise ReservationError(409, "That reservation is no longer scheduled")
    reservation.status = ReservationStatus.CANCELLED
    record_audit(
        db,
        actor=staff,
        action="reservation.cancelled",
        entity_type="reservation",
        entity_id=str(reservation.id),
        detail="cancelled",
    )
    db.commit()
    db.refresh(reservation)
    return reservation


def upcoming(db: Session, *, now: datetime | None = None) -> list[Reservation]:
    moment = _utc(now)
    horizon = moment + timedelta(days=2)
    return list(
        db.scalars(
            select(Reservation)
            .where(
                Reservation.status == ReservationStatus.SCHEDULED,
                Reservation.ends_at > moment,
                Reservation.starts_at < horizon,
            )
            .order_by(Reservation.starts_at)
        )
    )


def claim_for_start(db: Session, *, station: Station, reservation_id: str | None, started_at: datetime) -> Reservation | None:
    covering = db.scalar(
        select(Reservation).where(
            Reservation.station_id == station.id,
            Reservation.status == ReservationStatus.SCHEDULED,
            Reservation.starts_at <= started_at,
            Reservation.ends_at > started_at,
        )
    )
    if covering is None:
        if reservation_id:
            raise ReservationError(422, "That reservation does not cover this start time")
        return None
    if reservation_id is None or str(covering.id) != reservation_id:
        raise ReservationError(409, "This station is reserved")
    return covering


def mark_started(reservation: Reservation, session_id) -> None:
    reservation.status = ReservationStatus.STARTED
    reservation.session_id = session_id


def _reject_overlap(db: Session, station: Station, start: datetime, end: datetime) -> None:
    overlap = db.scalar(
        select(Reservation.id).where(
            Reservation.station_id == station.id,
            Reservation.status == ReservationStatus.SCHEDULED,
            Reservation.starts_at < end,
            Reservation.ends_at > start,
        )
    )
    if overlap is not None:
        raise ReservationError(409, "That station is already reserved then")


def _station(db: Session, code: str) -> Station:
    station = db.scalar(select(Station).where(Station.code == code))
    if station is None:
        raise ReservationError(404, "Station not found")
    if not station.is_customer_station or not station.is_billable:
        raise ReservationError(422, "This station cannot be reserved")
    if station.status != StationStatus.AVAILABLE:
        raise ReservationError(409, "This station is not available")
    return station


def _customer(db: Session, customer_id: str) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None or not customer.is_active:
        raise ReservationError(404, "Customer not found")
    return customer


def _utc(moment: datetime | None) -> datetime:
    current = moment or datetime.now(timezone.utc)
    if current.tzinfo is None:
        return current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)
