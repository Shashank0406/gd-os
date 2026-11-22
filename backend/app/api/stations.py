from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.models.station import Station
from app.schemas.catalog import StationOut
from app.services.agent import AgentError, desired_for_stations, pair_station

router = APIRouter(prefix="/stations", tags=["stations"])


class PairIn(BaseModel):
    mac_address: str
    hardware_uuid: str


def _call(action):
    try:
        return action()
    except AgentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("", response_model=list[StationOut])
def list_stations(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("stations.read")),
) -> list[StationOut]:
    stations = list(db.scalars(select(Station).order_by(Station.code)))
    desired = desired_for_stations(db, stations)
    return [
        StationOut.model_validate(station).model_copy(update={"agent_desired": desired[station.id]})
        for station in stations
    ]


@router.post("/{station_code}/agent", status_code=201)
def pair_agent(
    station_code: str,
    body: PairIn,
    db: Session = Depends(get_db),
    staff: User = Depends(require_permission("stations.manage")),
) -> dict[str, str]:
    paired = _call(
        lambda: pair_station(
            db,
            station_code=station_code,
            mac_address=body.mac_address,
            hardware_uuid=body.hardware_uuid,
            staff=staff,
        )
    )
    return {"station_code": station_code, "mac_address": paired.mac_address, "hardware_uuid": paired.hardware_uuid}
