from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.services.reports import kolkata_today, takings_for, utilisation_for

router = APIRouter(prefix="/reports", tags=["reports"])


class MethodTotal(BaseModel):
    method: str
    amount_rupees: str


class PaymentLine(BaseModel):
    recorded_at_local: str
    station_code: str
    method: str
    amount_rupees: str
    session_id: str


class TakingsOut(BaseModel):
    date: str
    timezone: str
    total_rupees: str
    by_method: list[MethodTotal]
    payments: list[PaymentLine]


@router.get("/takings", response_model=TakingsOut)
def takings(
    day: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("sessions.read")),
) -> TakingsOut:
    return TakingsOut.model_validate(takings_for(db, day or kolkata_today()))


class StationUse(BaseModel):
    station_code: str
    occupied_seconds: int
    session_count: int


class UtilisationOut(BaseModel):
    date: str
    timezone: str
    occupied_seconds: int
    stations: list[StationUse]


@router.get("/utilisation", response_model=UtilisationOut)
def utilisation(
    day: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("sessions.read")),
) -> UtilisationOut:
    return UtilisationOut.model_validate(
        utilisation_for(db, day or kolkata_today(), now=datetime.now(timezone.utc))
    )
