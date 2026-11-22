from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.seed import seed
from app.db.session import get_db
from app.main import app
from app.models.enums import BillingMode, PaymentMethod
from app.services.access import create_user
from app.services.sessions import end_session, start_session
from tests.staff_client import TEST_PASSWORD, staff_client

IST_MIDNIGHT_UTC = datetime(2026, 11, 21, 18, 30, tzinfo=timezone.utc)
NEXT_MIDNIGHT_UTC = datetime(2026, 11, 22, 18, 30, tzinfo=timezone.utc)
MORNING_UTC = datetime(2026, 11, 22, 4, 0, tzinfo=timezone.utc)


def test_takings_follow_the_kolkata_day(db) -> None:
    seed(db)
    cashier = create_user(
        db,
        username="report-desk",
        password=TEST_PASSWORD,
        display_name="Desk",
        role_name="CASHIER",
        actor=None,
    )
    start_session(
        db,
        station_code="PC-10",
        staff=cashier,
        billing_mode=BillingMode.PREPAID,
        guest_label="Midnight",
        duration_seconds=3600,
        payment_method=PaymentMethod.UPI,
        now=IST_MIDNIGHT_UTC,
    )
    morning = start_session(
        db,
        station_code="PC-09",
        staff=cashier,
        billing_mode=BillingMode.POSTPAID,
        guest_label="Morning",
        now=MORNING_UTC,
    )
    end_session(
        db,
        session_id=str(morning.id),
        staff=cashier,
        payment_method=PaymentMethod.CASH,
        now=MORNING_UTC + timedelta(minutes=1),
    )
    late = start_session(
        db,
        station_code="PC-11",
        staff=cashier,
        billing_mode=BillingMode.POSTPAID,
        guest_label="Next day",
        now=NEXT_MIDNIGHT_UTC,
    )
    end_session(
        db,
        session_id=str(late.id),
        staff=cashier,
        payment_method=PaymentMethod.CASH,
        now=NEXT_MIDNIGHT_UTC,
    )

    with staff_client(db, "CASHIER", "report-reader") as client:
        today = client.get("/reports/takings?date=2026-11-22")
        tomorrow = client.get("/reports/takings?date=2026-11-23")
        empty = client.get("/reports/takings?date=2026-11-01")

    assert today.status_code == 200, today.text
    body = today.json()
    assert body["timezone"] == "Asia/Kolkata"
    assert body["total_rupees"] == "152.50"
    amounts = {item["method"]: item["amount_rupees"] for item in body["by_method"]}
    assert amounts == {"CASH": "2.50", "UPI": "150.00", "CARD": "0.00", "FREE": "0.00"}
    assert [item["station_code"] for item in body["payments"]] == ["PC-10", "PC-09"]
    assert body["payments"][0]["recorded_at_local"].endswith("+05:30")
    assert tomorrow.json()["total_rupees"] == "2.50"
    assert tomorrow.json()["payments"][0]["station_code"] == "PC-11"
    assert empty.json()["total_rupees"] == "0.00"
    assert empty.json()["payments"] == []


def test_customer_cannot_read_takings(db) -> None:
    seed(db)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        registered = client.post(
            "/customers/register",
            json={
                "username": "no.report",
                "password": "player-pass-1",
                "display_name": "No Report",
                "mobile": "9876533333",
            },
        )
        token = registered.json()["access_token"]
        denied = client.get("/reports/takings", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()
    assert denied.status_code == 401
