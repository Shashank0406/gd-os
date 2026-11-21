from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.seed import seed
from app.db.session import get_db
from app.main import app
from app.models.customer import Customer
from app.models.enums import BillingMode, DeviceType, PaymentMethod, StationStatus
from app.models.pricing import Package, PricingPlan
from app.models.station import Station
from app.services.access import create_user
from app.services.customers import register_customer
from app.services.sessions import SessionError, end_session, extend_session, start_session
from tests.staff_client import TEST_PASSWORD, staff_client

START = datetime(2026, 11, 22, 4, 0, tzinfo=timezone.utc)


def _cashier(db):
    return create_user(
        db,
        username="desk-sessions",
        password=TEST_PASSWORD,
        display_name="Desk",
        role_name="CASHIER",
        actor=None,
    )


def test_postpaid_hour_keeps_the_starting_price(db) -> None:
    seed(db)
    staff = _cashier(db)
    play = start_session(
        db,
        station_code="PC-01",
        staff=staff,
        billing_mode=BillingMode.POSTPAID,
        guest_label="Guest",
        now=START,
    )
    plan = db.scalar(select(PricingPlan).where(PricingPlan.device_type == DeviceType.PC, PricingPlan.station_id.is_(None)))
    assert plan is not None
    plan.hourly_rate_rupees = Decimal("180.00")
    db.commit()

    ended = end_session(db, session_id=str(play.id), staff=staff, payment_method=PaymentMethod.CASH, now=START + timedelta(hours=1))

    assert ended.final_amount_rupees == Decimal("150.00")
    assert ended.hourly_rate_rupees == Decimal("150.00")
    station = db.get(Station, play.station_id)
    assert station is not None
    assert station.status == StationStatus.AVAILABLE


def test_second_start_on_the_same_station_is_rejected(db) -> None:
    seed(db)
    staff = _cashier(db)
    start_session(db, station_code="PC-02", staff=staff, billing_mode=BillingMode.POSTPAID, guest_label="One", now=START)
    with pytest.raises(SessionError) as raised:
        start_session(db, station_code="PC-02", staff=staff, billing_mode=BillingMode.POSTPAID, guest_label="Two", now=START)
    assert raised.value.status_code == 409


def test_cashier_workstation_cannot_start_a_session(db) -> None:
    seed(db)
    staff = _cashier(db)
    with pytest.raises(SessionError) as raised:
        start_session(db, station_code="CASHIER-01", staff=staff, billing_mode=BillingMode.POSTPAID, guest_label="Desk", now=START)
    assert raised.value.status_code == 422


def test_prepaid_package_does_not_refund_an_early_end_and_bills_overtime(db) -> None:
    seed(db)
    staff = _cashier(db)
    play = start_session(
        db,
        station_code="PS5-01",
        staff=staff,
        billing_mode=BillingMode.PREPAID,
        guest_label="PS guest",
        package_code="PS5-1H",
        payment_method=PaymentMethod.UPI,
        now=START,
    )
    early = end_session(db, session_id=str(play.id), staff=staff, now=START + timedelta(minutes=20))
    assert early.final_amount_rupees == Decimal("250.00")

    package = db.scalar(select(Package).where(Package.code == "PS5-1H"))
    assert package is not None
    package.price_rupees = Decimal("999.00")
    db.commit()
    second = start_session(
        db,
        station_code="PS5-01",
        staff=staff,
        billing_mode=BillingMode.PREPAID,
        guest_label="PS guest 2",
        package_code="PS5-1H",
        payment_method=PaymentMethod.CASH,
        now=START,
    )
    overtime = end_session(
        db,
        session_id=str(second.id),
        staff=staff,
        payment_method=PaymentMethod.CASH,
        now=START + timedelta(hours=1, seconds=1),
    )
    assert overtime.package_price_rupees == Decimal("999.00")
    assert overtime.final_amount_rupees == Decimal("1003.17")


def test_prepaid_extension_is_charged_immediately(db) -> None:
    seed(db)
    staff = _cashier(db)
    play = start_session(
        db,
        station_code="SIM-01",
        staff=staff,
        billing_mode=BillingMode.PREPAID,
        guest_label="Racer",
        duration_seconds=3600,
        payment_method=PaymentMethod.CARD,
        now=START,
    )
    assert play.final_amount_rupees is None
    extended = extend_session(
        db,
        session_id=str(play.id),
        staff=staff,
        duration_seconds=1800,
        payment_method=PaymentMethod.CARD,
        now=START + timedelta(minutes=30),
    )
    ended = end_session(db, session_id=str(extended.id), staff=staff, now=START + timedelta(minutes=90))
    assert ended.final_amount_rupees == Decimal("1200.00")


def test_free_play_ends_at_zero(db) -> None:
    seed(db)
    staff = _cashier(db)
    play = start_session(db, station_code="PC-03", staff=staff, billing_mode=BillingMode.FREE_PLAY, guest_label="Comp", now=START)
    ended = end_session(db, session_id=str(play.id), staff=staff, now=START + timedelta(hours=2))
    assert ended.final_amount_rupees == Decimal("0.00")


def test_one_customer_cannot_hold_two_stations(db) -> None:
    seed(db)
    staff = _cashier(db)
    customer = register_customer(db, username="session.player", password="player-pass-1", display_name="Player", mobile="9876500000")
    start_session(db, station_code="PC-04", staff=staff, billing_mode=BillingMode.POSTPAID, customer_id=str(customer.id), now=START)
    with pytest.raises(SessionError) as raised:
        start_session(db, station_code="PC-05", staff=staff, billing_mode=BillingMode.POSTPAID, customer_id=str(customer.id), now=START)
    assert raised.value.status_code == 409
    assert db.get(Customer, customer.id) is not None


def test_cashier_can_start_and_end_from_the_api(db) -> None:
    seed(db)
    with staff_client(db, "CASHIER", "desk-api") as client:
        started = client.post(
            "/sessions",
            json={"station_code": "PC-06", "billing_mode": "POSTPAID", "guest_label": "Walk up"},
        )
        assert started.status_code == 201, started.text
        body = started.json()
        assert body["hourly_rate_rupees"] == "150.00"
        assert body["started_at_local"].endswith("+05:30")
        ended = client.post(f"/sessions/{body['id']}/end", json={"payment_method": "CASH"})
    assert ended.status_code == 200, ended.text
    assert ended.json()["final_amount_rupees"] == "2.50"
    assert ended.json()["amount_paid_rupees"] == "2.50"


def test_customer_cannot_start_a_session(db) -> None:
    seed(db)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        registered = client.post(
            "/customers/register",
            json={
                "username": "no.session",
                "password": "player-pass-1",
                "display_name": "No Session",
                "mobile": "9876511111",
            },
        )
        token = registered.json()["access_token"]
        denied = client.post(
            "/sessions",
            headers={"Authorization": f"Bearer {token}"},
            json={"station_code": "PC-07", "billing_mode": "POSTPAID", "guest_label": "Nope"},
        )
    finally:
        app.dependency_overrides.clear()
    assert denied.status_code == 401
