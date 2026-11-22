from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.agent import AgentError, heartbeat

router = APIRouter(prefix="/agent", tags=["agent"])


class HeartbeatIn(BaseModel):
    mac_address: str
    hardware_uuid: str


class HeartbeatOut(BaseModel):
    station_code: str
    desired: str
    session_id: str | None
    server_time_utc: str


def _call(action):
    try:
        return action()
    except AgentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/heartbeat", response_model=HeartbeatOut)
def agent_heartbeat(body: HeartbeatIn, db: Session = Depends(get_db)) -> HeartbeatOut:
    station, desired, session_id = _call(
        lambda: heartbeat(db, mac_address=body.mac_address, hardware_uuid=body.hardware_uuid)
    )
    return HeartbeatOut(
        station_code=station.code,
        desired=desired,
        session_id=session_id,
        server_time_utc=datetime.now(timezone.utc).isoformat(),
    )
