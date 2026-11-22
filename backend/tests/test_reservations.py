from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.seed import seed
from app.db.session import get_db
from app.main import app
from app.models.enums import BillingMode, ReservationStatus
from app.models.reservation import Reservation
from tests.staff_client import staff_client

def _now() -> datetime:
    return datetime.now(timezone.utc)


def test_overlapping_reservation_is_rejected_and_a_start_uses_the_hold(db) -> None:
    seed(db)
    with staff_client(db, "CASHIER", "reserve-desk") as client:
        booked = client.post(
            "/reservations",
            json={
                "station_code": "PC-12",
                "guest_label": "Ravi",
                "starts_at": _now().isoformat(),
                "duration_seconds": 3600,
            },
        )
        assert booked.status_code == 201, booked.text
        body = booked.json()
        assert body["holder_name"] == "Ravi"
        assert body["starts_at_local"].endswith("+05:30")
        reservation_id = body["id"]

        overlap = client.post(
            "/reservations",
            json={
                "station_code": "PC-12",
                "guest_label": "Other",
                "starts_at": (_now() + timedelta(minutes=30)).isoformat(),
                "duration_seconds": 3600,
            },
        )
        assert overlap.status_code == 409

        adjacent = client.post(
            "/reservations",
            json={
                "station_code": "PC-12",
                "guest_label": "Later",
                "starts_at": (_now() + timedelta(hours=1)).isoformat(),
                "duration_seconds": 1800,
            },
        )
        assert adjacent.status_code == 201, adjacent.text

        blocked = client.post(
            "/sessions",
            json={"station_code": "PC-12", "billing_mode": "POSTPAID", "guest_label": "Walk in"},
        )
        assert blocked.status_code == 409

        started = client.post(
            "/sessions",
            json={
                "station_code": "PC-12",
                "billing_mode": "POSTPAID",
                "guest_label": "Ravi",
                "reservation_id": reservation_id,
            },
        )
        assert started.status_code == 201, started.text

    reservation = db.get(Reservation, reservation_id)
    assert reservation is not None
    assert reservation.status == ReservationStatus.STARTED


def test_future_reservation_does_not_block_play_now(db) -> None:
    seed(db)
    with staff_client(db, "CASHIER", "reserve-later") as client:
        later = _now() + timedelta(hours=3)
        booked = client.post(
            "/reservations",
            json={
                "station_code": "PS5-02",
                "guest_label": "Evening",
                "starts_at": later.isoformat(),
                "duration_seconds": 3600,
            },
        )
        assert booked.status_code == 201, booked.text
        started = client.post(
            "/sessions",
            json={"station_code": "PS5-02", "billing_mode": "POSTPAID", "guest_label": "Now"},
        )
        assert started.status_code == 201, started.text
        listed = client.get("/reservations")
        assert any(item["holder_name"] == "Evening" for item in listed.json())


def test_cashier_station_cannot_be_reserved_and_a_customer_cannot_book(db) -> None:
    seed(db)
    with staff_client(db, "CASHIER", "reserve-block") as client:
        denied = client.post(
            "/reservations",
            json={
                "station_code": "CASHIER-01",
                "guest_label": "Desk",
                "starts_at": _now().isoformat(),
                "duration_seconds": 1800,
            },
        )
        assert denied.status_code == 422
        past = client.post(
            "/reservations",
            json={
                "station_code": "PC-13",
                "guest_label": "Old",
                "starts_at": "2020-01-01T00:00:00Z",
                "duration_seconds": 1800,
            },
        )
        assert past.status_code == 422

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        registered = client.post(
            "/customers/register",
            json={
                "username": "no.reserve",
                "password": "player-pass-1",
                "display_name": "No Reserve",
                "mobile": "9876544444",
            },
        )
        token = registered.json()["access_token"]
        denied = client.post(
            "/reservations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "station_code": "PC-13",
                "guest_label": "Nope",
                "starts_at": _now().isoformat(),
                "duration_seconds": 1800,
            },
        )
    finally:
        app.dependency_overrides.clear()
    assert denied.status_code == 401
