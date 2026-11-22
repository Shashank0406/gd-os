"""Takings for one café day. The day is Asia/Kolkata, not UTC."""

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
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
