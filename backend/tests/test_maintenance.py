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


def test_manager_can_take_a_station_out_and_a_cashier_cannot(db) -> None:
    seed(db)
    with staff_client(db, "MANAGER", "floor-manager") as client:
        changed = client.post(
            "/stations/PC-15/status",
            json={"status": "MAINTENANCE", "reason": "Fan check"},
        )
        assert changed.status_code == 200, changed.text
        body = changed.json()
        assert body["status"] == "MAINTENANCE"
        assert body["maintenance_reason"] == "Fan check"
        blocked = client.post(
            "/sessions",
            json={"station_code": "PC-15", "billing_mode": "POSTPAID", "guest_label": "Guest"},
        )
        assert blocked.status_code == 409
        held = client.post(
            "/reservations",
            json={
                "station_code": "PC-15",
                "guest_label": "Later",
                "starts_at": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": 1800,
            },
        )
        assert held.status_code == 409
        restored = client.post("/stations/PC-15/status", json={"status": "AVAILABLE"})
        assert restored.status_code == 200
        assert restored.json()["status"] == "AVAILABLE"
        assert restored.json()["maintenance_reason"] is None

    with staff_client(db, "CASHIER", "floor-cashier") as client:
        denied = client.post(
            "/stations/PC-15/status",
            json={"status": "DISABLED", "reason": "Retired"},
        )
    assert denied.status_code == 403


def test_open_session_blocks_maintenance_and_end_returns_the_station(db) -> None:
    seed(db)
    cashier = create_user(
        db,
        username="session-desk",
        password=TEST_PASSWORD,
        display_name="Desk",
        role_name="CASHIER",
        actor=None,
    )
    play = start_session(
        db,
        station_code="PC-12",
        staff=cashier,
        billing_mode=BillingMode.POSTPAID,
        guest_label="Still playing",
        now=START,
    )
    with staff_client(db, "SUPER_ADMIN", "floor-admin") as client:
        busy = client.post("/stations/PC-12/status", json={"status": "MAINTENANCE", "reason": "Now"})
        assert busy.status_code == 409
        cashier_station = client.post("/stations/CASHIER-01/status", json={"status": "DISABLED", "reason": "No"})
        assert cashier_station.status_code == 422
    end_session(
        db,
        session_id=str(play.id),
        staff=cashier,
        payment_method=PaymentMethod.CASH,
        now=START + timedelta(minutes=1),
    )
    with staff_client(db, "SUPER_ADMIN", "floor-admin-2") as client:
        listed = client.get("/stations")
        row = next(item for item in listed.json() if item["code"] == "PC-12")
        assert row["status"] == "AVAILABLE"


def test_customer_cannot_change_station_status(db) -> None:
    seed(db)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        registered = client.post(
            "/customers/register",
            json={
                "username": "no.status",
                "password": "player-pass-1",
                "display_name": "No Status",
                "mobile": "9876554444",
            },
        )
        token = registered.json()["access_token"]
        denied = client.post(
            "/stations/PC-15/status",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "DISABLED", "reason": "No"},
        )
    finally:
        app.dependency_overrides.clear()
    assert denied.status_code == 401
