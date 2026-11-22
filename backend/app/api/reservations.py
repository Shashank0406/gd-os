import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.customer import Customer
from app.models.enums import ReservationStatus
from app.models.identity import User
from app.models.reservation import Reservation
from app.models.station import Station
from app.services.reservations import ReservationError, book_reservation, cancel_reservation, upcoming

router = APIRouter(prefix="/reservations", tags=["reservations"])
KOLKATA = ZoneInfo("Asia/Kolkata")


class BookIn(BaseModel):
    station_code: str
    starts_at: datetime
    duration_seconds: int
    customer_id: uuid.UUID | None = None
    guest_label: str | None = None


class ReservationOut(BaseModel):
    id: str
    station_code: str
    holder_name: str
    status: ReservationStatus
    starts_at_utc: str
    starts_at_local: str
    ends_at_utc: str
    ends_at_local: str


def _local(moment: datetime) -> str:
    return moment.astimezone(KOLKATA).isoformat()


def _out(db: Session, reservation: Reservation) -> ReservationOut:
    station = db.get(Station, reservation.station_id)
    customer = db.get(Customer, reservation.customer_id) if reservation.customer_id else None
    holder = reservation.guest_label or ("" if customer is None else customer.display_name)
    return ReservationOut(
        id=str(reservation.id),
        station_code="" if station is None else station.code,
        holder_name=holder,
        status=reservation.status,
        starts_at_utc=reservation.starts_at.isoformat(),
        starts_at_local=_local(reservation.starts_at),
        ends_at_utc=reservation.ends_at.isoformat(),
        ends_at_local=_local(reservation.ends_at),
    )


def _call(action):
    try:
        return action()
    except ReservationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("", response_model=list[ReservationOut])
def list_upcoming(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("sessions.read")),
) -> list[ReservationOut]:
    return [_out(db, reservation) for reservation in upcoming(db)]


@router.post("", response_model=ReservationOut, status_code=201)
def book(
    body: BookIn,
    db: Session = Depends(get_db),
    staff: User = Depends(require_permission("sessions.operate")),
) -> ReservationOut:
    reservation = _call(
        lambda: book_reservation(
            db,
            station_code=body.station_code,
            staff=staff,
            starts_at=body.starts_at,
            duration_seconds=body.duration_seconds,
            customer_id=None if body.customer_id is None else str(body.customer_id),
            guest_label=body.guest_label,
        )
    )
    return _out(db, reservation)


@router.post("/{reservation_id}/cancel", response_model=ReservationOut)
def cancel(
    reservation_id: uuid.UUID,
    db: Session = Depends(get_db),
    staff: User = Depends(require_permission("sessions.operate")),
) -> ReservationOut:
    reservation = _call(lambda: cancel_reservation(db, reservation_id=str(reservation_id), staff=staff))
    return _out(db, reservation)
