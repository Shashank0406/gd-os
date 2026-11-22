from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.services.reports import kolkata_today, takings_for

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
