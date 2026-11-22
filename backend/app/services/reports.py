"""Takings and station use for one café day. The day is Asia/Kolkata, not UTC."""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import PaymentMethod
from app.models.play_session import Payment, PlaySession
from app.models.station import Station
from app.schemas.money import rupees, rupees_text

KOLKATA = ZoneInfo("Asia/Kolkata")
METHODS = (PaymentMethod.CASH, PaymentMethod.UPI, PaymentMethod.CARD, PaymentMethod.FREE)


def kolkata_today(now: datetime | None = None) -> date:
    moment = now or datetime.now(KOLKATA)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ZoneInfo("UTC"))
    return moment.astimezone(KOLKATA).date()


def takings_for(db: Session, day: date) -> dict:
    local_day = func.date(func.timezone("Asia/Kolkata", Payment.recorded_at))
    rows = db.execute(
        select(Payment, Station.code)
        .join(PlaySession, PlaySession.id == Payment.session_id)
        .join(Station, Station.id == PlaySession.station_id)
        .where(local_day == day)
        .order_by(Payment.recorded_at, Payment.id)
    ).all()
    totals = {method: Decimal("0.00") for method in METHODS}
    payments = []
    for payment, station_code in rows:
        amount = rupees(payment.amount_rupees)
        totals[payment.method] = rupees(totals[payment.method] + amount)
        recorded = payment.recorded_at
        if recorded.tzinfo is None:
            recorded = recorded.replace(tzinfo=ZoneInfo("UTC"))
        payments.append(
            {
                "recorded_at_local": recorded.astimezone(KOLKATA).isoformat(),
                "station_code": station_code,
                "method": payment.method.value,
                "amount_rupees": rupees_text(amount),
                "session_id": str(payment.session_id),
            }
        )
    total = rupees(sum(totals.values(), Decimal("0.00")))
    return {
        "date": day.isoformat(),
        "timezone": "Asia/Kolkata",
        "total_rupees": rupees_text(total),
        "by_method": [{"method": method.value, "amount_rupees": rupees_text(totals[method])} for method in METHODS],
        "payments": payments,
    }


def utilisation_for(db: Session, day: date, now: datetime | None = None) -> dict:
    moment = _utc(now)
    day_start = datetime.combine(day, time.min, tzinfo=KOLKATA)
    day_end = day_start + timedelta(days=1)
    stations = list(db.scalars(select(Station).where(Station.is_billable.is_(True)).order_by(Station.code)))
    station_ids = [station.id for station in stations]
    sessions = []
    if station_ids:
        sessions = list(
            db.scalars(
                select(PlaySession).where(
                    PlaySession.station_id.in_(station_ids),
                    PlaySession.started_at < day_end,
                    or_(PlaySession.ended_at.is_(None), PlaySession.ended_at > day_start),
                )
            )
        )
    occupied = {station.id: 0 for station in stations}
    counts = {station.id: 0 for station in stations}
    for play in sessions:
        begin = _utc(play.started_at)
        stop = _utc(play.ended_at) if play.ended_at is not None else moment
        clip_start = max(begin, day_start)
        clip_end = min(stop, day_end, moment)
        if clip_end <= clip_start:
            continue
        occupied[play.station_id] += int((clip_end - clip_start).total_seconds())
        counts[play.station_id] += 1
    rows = [
        {
            "station_code": station.code,
            "occupied_seconds": occupied[station.id],
            "session_count": counts[station.id],
        }
        for station in stations
    ]
    return {
        "date": day.isoformat(),
        "timezone": "Asia/Kolkata",
        "occupied_seconds": sum(occupied.values()),
        "stations": rows,
    }


def _utc(moment: datetime | None) -> datetime:
    current = moment or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)
