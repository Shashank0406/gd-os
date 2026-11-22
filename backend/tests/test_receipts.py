from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.seed import seed
from app.db.session import get_db
from app.main import app
from app.models.enums import BillingMode, PaymentMethod
from app.services.access import create_user
from app.services.sessions import end_session, start_session
from tests.staff_client import TEST_PASSWORD, staff_client

START = datetime(2026, 11, 22, 4, 0, tzinfo=timezone.utc)


def test_closed_session_has_a_receipt_and_an_open_one_does_not(db) -> None:
    seed(db)
    cashier = create_user(
        db,
        username="receipt-desk",
        password=TEST_PASSWORD,
        display_name="Desk",
        role_name="CASHIER",
        actor=None,
    )
    play = start_session(
        db,
        station_code="PC-15",
        staff=cashier,
        billing_mode=BillingMode.POSTPAID,
        guest_label="Receipt guest",
        now=START,
    )
    with staff_client(db, "CASHIER", "receipt-reader") as client:
        early = client.get(f"/sessions/{play.id}/receipt")
        assert early.status_code == 409
        end_session(
            db,
            session_id=str(play.id),
            staff=cashier,
            payment_method=PaymentMethod.UPI,
            now=START + timedelta(minutes=1),
        )
        slip = client.get(f"/sessions/{play.id}/receipt")
    assert slip.status_code == 200, slip.text
    body = slip.json()
    assert body["station_code"] == "PC-15"
    assert body["holder_name"] == "Receipt guest"
    assert body["final_amount_rupees"] == "2.50"
    assert body["amount_paid_rupees"] == "2.50"
    assert body["payments"] == [{"method": "UPI", "amount_rupees": "2.50"}]
    assert body["started_at_local"].endswith("+05:30")
    assert body["ended_at_local"].endswith("+05:30")


def test_customer_cannot_read_a_receipt(db) -> None:
    seed(db)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        registered = client.post(
            "/customers/register",
            json={
                "username": "no.receipt",
                "password": "player-pass-1",
                "display_name": "No Receipt",
                "mobile": "9876555555",
            },
        )
        token = registered.json()["access_token"]
        denied = client.get(
            "/sessions/11111111-1111-4111-8111-111111111111/receipt",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.clear()
    assert denied.status_code == 401
