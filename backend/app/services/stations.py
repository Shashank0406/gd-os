"""Take a station out of play, and put it back."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import StationStatus
from app.models.identity import User
from app.models.station import Station
from app.services.access import record_audit

SETTABLE = {StationStatus.AVAILABLE, StationStatus.MAINTENANCE, StationStatus.DISABLED}
OUT_OF_PLAY = {StationStatus.MAINTENANCE, StationStatus.DISABLED}


class StationError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def set_station_status(
    db: Session,
    *,
    station_code: str,
    status: StationStatus,
    reason: str | None,
    staff: User,
) -> Station:
    if status not in SETTABLE:
        raise StationError(422, "Choose available, maintenance, or disabled")
    station = db.scalar(select(Station).where(Station.code == station_code))
    if station is None:
        raise StationError(404, "Station not found")
    if not station.is_customer_station or not station.is_billable:
        raise StationError(422, "This station stays on the floor")
    if station.status == StationStatus.IN_SESSION:
        raise StationError(409, "Close the session before changing this station")
    if station.status not in SETTABLE:
        raise StationError(409, "This station cannot change status right now")
    note = "" if reason is None else reason.strip()
    if status in OUT_OF_PLAY:
        if not note:
            raise StationError(422, "Enter a reason")
        if len(note) > 200:
            raise StationError(422, "Reason is too long")
        station.maintenance_reason = note
    else:
        station.maintenance_reason = None
    station.status = status
    record_audit(
        db,
        actor=staff,
        action="station.status_changed",
        entity_type="station",
        entity_id=str(station.id),
        detail=f"code={station.code}; status={status.value}; reason={note}",
    )
    db.commit()
    db.refresh(station)
    return station
