from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.models.station import Station
from app.schemas.catalog import StationOut

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("", response_model=list[StationOut])
def list_stations(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("stations.read")),
) -> list[Station]:
    return list(db.scalars(select(Station).order_by(Station.code)))
