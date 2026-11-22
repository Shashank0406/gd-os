"""Pair a diskless PC and tell it whether to lock. The PC does not choose."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.agent import StationAgent
from app.models.enums import DeviceType, SessionStatus
from app.models.identity import User
from app.models.play_session import PlaySession
from app.models.station import Station
from app.services.access import record_audit


class AgentError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def normalize_mac(value: str) -> str:
    raw = value.strip().lower().replace("-", "").replace(":", "")
    if len(raw) != 12 or any(character not in "0123456789abcdef" for character in raw):
        raise AgentError(422, "MAC address must be 12 hex digits")
    return ":".join(raw[index : index + 2] for index in range(0, 12, 2))


def normalize_hardware_uuid(value: str) -> str:
    try:
        return str(uuid.UUID(value.strip())).lower()
    except ValueError as exc:
        raise AgentError(422, "Hardware id must be a UUID") from exc


def pair_station(db: Session, *, station_code: str, mac_address: str, hardware_uuid: str, staff: User) -> StationAgent:
    mac = normalize_mac(mac_address)
    hardware = normalize_hardware_uuid(hardware_uuid)
    station = db.scalar(select(Station).where(Station.code == station_code))
    if station is None:
        raise AgentError(404, "Station not found")
    if station.device_type != DeviceType.PC:
        raise AgentError(422, "Only a gaming PC runs an agent")
    existing = db.get(StationAgent, station.id)
    if existing is None:
        existing = StationAgent(station_id=station.id, mac_address=mac, hardware_uuid=hardware, paired_by_user_id=staff.id)
        db.add(existing)
    else:
        existing.mac_address = mac
        existing.hardware_uuid = hardware
        existing.paired_by_user_id = staff.id
    record_audit(
        db,
        actor=staff,
        action="station.agent_paired",
        entity_type="station",
        entity_id=str(station.id),
        detail=f"station={station.code}; mac={mac}",
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AgentError(409, "That MAC address or hardware id is already paired to another station") from exc
    db.refresh(existing)
    return existing


def heartbeat(db: Session, *, mac_address: str, hardware_uuid: str, now: datetime | None = None) -> tuple[Station, str, str | None]:
    mac = normalize_mac(mac_address)
    hardware = normalize_hardware_uuid(hardware_uuid)
    by_mac = db.scalar(select(StationAgent).where(StationAgent.mac_address == mac))
    by_hardware = db.scalar(select(StationAgent).where(StationAgent.hardware_uuid == hardware))
    if by_mac is None and by_hardware is None:
        raise AgentError(404, "This PC is not paired")
    if by_mac is None or by_hardware is None or by_mac.station_id != by_hardware.station_id:
        raise AgentError(409, "MAC address and hardware id do not match a paired PC")
    station = db.get(Station, by_mac.station_id)
    if station is None:
        raise AgentError(404, "Station not found")
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    station.last_heartbeat_at = moment.astimezone(timezone.utc)
    session_id = db.scalar(
        select(PlaySession.id).where(
            PlaySession.station_id == station.id,
            PlaySession.status == SessionStatus.ACTIVE,
        )
    )
    desired = "UNLOCK" if session_id is not None else "LOCK"
    db.commit()
    db.refresh(station)
    return station, desired, None if session_id is None else str(session_id)


def desired_for_stations(db: Session, stations: list[Station]) -> dict[uuid.UUID, str | None]:
    pc_ids = [station.id for station in stations if station.device_type == DeviceType.PC]
    if not pc_ids:
        return {station.id: None for station in stations}
    paired = set(db.scalars(select(StationAgent.station_id).where(StationAgent.station_id.in_(pc_ids))))
    active = set(
        db.scalars(
            select(PlaySession.station_id).where(
                PlaySession.station_id.in_(pc_ids),
                PlaySession.status == SessionStatus.ACTIVE,
            )
        )
    )
    result: dict[uuid.UUID, str | None] = {}
    for station in stations:
        if station.device_type != DeviceType.PC:
            result[station.id] = None
        elif station.id not in paired:
            result[station.id] = "UNPAIRED"
        elif station.id in active:
            result[station.id] = "UNLOCK"
        else:
            result[station.id] = "LOCK"
    return result
