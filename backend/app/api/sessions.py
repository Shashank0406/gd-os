import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.enums import BillingMode, PaymentMethod, SessionStatus
from app.models.identity import User
from app.models.play_session import Payment, PlaySession
from app.models.station import Station
from app.schemas.money import rupees, rupees_text
from app.services.sessions import SessionError, amount_due_at, end_session, extend_session, start_session

router = APIRouter(prefix="/sessions", tags=["sessions"])
KOLKATA = ZoneInfo("Asia/Kolkata")


class StartIn(BaseModel):
    station_code: str
    billing_mode: BillingMode
    customer_id: uuid.UUID | None = None
    guest_label: str | None = None
    package_code: str | None = None
    duration_seconds: int | None = None
    payment_method: PaymentMethod | None = None


class ExtendIn(BaseModel):
    duration_seconds: int
    payment_method: PaymentMethod | None = None


class EndIn(BaseModel):
    payment_method: PaymentMethod | None = None


class DueOut(BaseModel):
    final_amount_rupees: str
    amount_paid_rupees: str
    balance_rupees: str
    as_of_local: str


class SessionOut(BaseModel):
    id: str
    station_code: str
    status: SessionStatus
    billing_mode: BillingMode
    hourly_rate_rupees: str
    package_code: str | None
    purchased_seconds: int
    final_amount_rupees: str | None
    amount_paid_rupees: str
    started_at_utc: str
    started_at_local: str
    ended_at_utc: str | None


def _local(moment: datetime) -> str:
    return moment.astimezone(KOLKATA).isoformat()


def _out(db: Session, play: PlaySession) -> SessionOut:
    station = db.get(Station, play.station_id)
    paid = db.scalars(select(Payment.amount_rupees).where(Payment.session_id == play.id))
    paid_total = sum(paid, 0)
    return SessionOut(
        id=str(play.id),
        station_code="" if station is None else station.code,
        status=play.status,
        billing_mode=play.billing_mode,
        hourly_rate_rupees=rupees_text(play.hourly_rate_rupees),
        package_code=play.package_code,
        purchased_seconds=play.purchased_seconds,
        final_amount_rupees=None if play.final_amount_rupees is None else rupees_text(play.final_amount_rupees),
        amount_paid_rupees=rupees_text(paid_total),
        started_at_utc=play.started_at.isoformat(),
        started_at_local=_local(play.started_at),
        ended_at_utc=None if play.ended_at is None else play.ended_at.isoformat(),
    )


def _call(db: Session, action):
    try:
        return action()
    except SessionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/active", response_model=list[SessionOut])
def list_active(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("sessions.read")),
) -> list[SessionOut]:
    rows = db.scalars(select(PlaySession).where(PlaySession.status == SessionStatus.ACTIVE).order_by(PlaySession.started_at))
    return [_out(db, play) for play in rows]


@router.post("", response_model=SessionOut, status_code=201)
def start(
    body: StartIn,
    db: Session = Depends(get_db),
    staff: User = Depends(require_permission("sessions.operate")),
) -> SessionOut:
    play = _call(
        db,
        lambda: start_session(
            db,
            station_code=body.station_code,
            staff=staff,
            billing_mode=body.billing_mode,
            customer_id=None if body.customer_id is None else str(body.customer_id),
            guest_label=body.guest_label,
            package_code=body.package_code,
            duration_seconds=body.duration_seconds,
            payment_method=body.payment_method,
        ),
    )
    return _out(db, play)


@router.get("/{session_id}/due", response_model=DueOut)
def due(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("sessions.read")),
) -> DueOut:
    play = db.get(PlaySession, session_id)
    if play is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if play.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Session is already closed")
    moment = datetime.now(timezone.utc)
    final_amount = amount_due_at(play, moment)
    paid = db.scalars(select(Payment.amount_rupees).where(Payment.session_id == play.id))
    paid_total = rupees(sum(paid, 0))
    balance = rupees(final_amount - paid_total)
    if balance < 0:
        balance = rupees(0)
    return DueOut(
        final_amount_rupees=rupees_text(final_amount),
        amount_paid_rupees=rupees_text(paid_total),
        balance_rupees=rupees_text(balance),
        as_of_local=_local(moment),
    )


@router.post("/{session_id}/extend", response_model=SessionOut)
def extend(
    session_id: uuid.UUID,
    body: ExtendIn,
    db: Session = Depends(get_db),
    staff: User = Depends(require_permission("sessions.operate")),
) -> SessionOut:
    play = _call(
        db,
        lambda: extend_session(
            db,
            session_id=str(session_id),
            staff=staff,
            duration_seconds=body.duration_seconds,
            payment_method=body.payment_method,
        ),
    )
    return _out(db, play)


@router.post("/{session_id}/end", response_model=SessionOut)
def end(
    session_id: uuid.UUID,
    body: EndIn,
    db: Session = Depends(get_db),
    staff: User = Depends(require_permission("sessions.operate")),
) -> SessionOut:
    play = _call(
        db,
        lambda: end_session(
            db,
            session_id=str(session_id),
            staff=staff,
            payment_method=body.payment_method,
        ),
    )
    return _out(db, play)
