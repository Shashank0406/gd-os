from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.seed import seed
from app.db.session import get_db
from app.main import app
from app.models.enums import BillingMode, DeviceType, PaymentMethod
from app.models.pricing import PricingPlan
from app.services.access import create_user
from app.services.sessions import end_session, start_session
from tests.staff_client import TEST_PASSWORD, staff_client

PEAK = datetime(2026, 11, 23, 13, 0, tzinfo=timezone.utc)
OFF_PEAK = datetime(2026, 11, 23, 11, 0, tzinfo=timezone.utc)


def _pc_plan(db) -> PricingPlan:
    plan = db.scalar(
        select(PricingPlan).where(PricingPlan.device_type == DeviceType.PC, PricingPlan.station_id.is_(None))
    )
    assert plan is not None
    return plan


def test_a_peak_window_prices_a_new_session_and_leaves_the_base_rate_outside_it(db) -> None:
    seed(db)
    plan = _pc_plan(db)
    cashier = create_user(
        db,
        username="peak-desk",
        password=TEST_PASSWORD,
        display_name="Desk",
        role_name="CASHIER",
        actor=None,
    )
    with staff_client(db, "SUPER_ADMIN", "peak-admin") as client:
        created = client.post(
            f"/pricing/plans/{plan.id}/schedules",
            json={
                "label": "Weekday peak",
                "days_of_week": [1, 2, 3, 4, 5],
                "start_local_time": "18:00:00",
                "end_local_time": "23:00:00",
                "hourly_rate_rupees": "200.00",
            },
        )
        assert created.status_code == 201, created.text
        overlap = client.post(
            f"/pricing/plans/{plan.id}/schedules",
            json={
                "label": "Also peak",
                "days_of_week": [1],
                "start_local_time": "17:00:00",
                "end_local_time": "19:00:00",
                "hourly_rate_rupees": "220.00",
            },
        )
        assert overlap.status_code == 409
        catalog = client.get("/pricing")
        pc = next(item for item in catalog.json()["plans"] if item["id"] == str(plan.id))
        assert pc["hourly_rate_rupees"] == "150.00"

    peak = start_session(
        db,
        station_code="PC-08",
        staff=cashier,
        billing_mode=BillingMode.POSTPAID,
        guest_label="Peak guest",
        now=PEAK,
    )
    assert peak.hourly_rate_rupees == Decimal("200.00")
    ended = end_session(
        db,
        session_id=str(peak.id),
        staff=cashier,
        payment_method=PaymentMethod.CASH,
        now=PEAK + timedelta(minutes=1),
    )
    assert ended.final_amount_rupees == Decimal("3.33")

    quiet = start_session(
        db,
        station_code="PC-09",
        staff=cashier,
        billing_mode=BillingMode.POSTPAID,
        guest_label="Quiet guest",
        now=OFF_PEAK,
    )
    assert quiet.hourly_rate_rupees == Decimal("150.00")


def test_cashier_cannot_add_a_schedule_and_a_package_keeps_its_price(db) -> None:
    seed(db)
    plan = db.scalar(
        select(PricingPlan).where(
            PricingPlan.device_type == DeviceType.PS5,
            PricingPlan.station_id.is_(None),
        )
    )
    assert plan is not None
    with staff_client(db, "CASHIER", "no-peak") as client:
        denied = client.post(
            f"/pricing/plans/{plan.id}/schedules",
            json={
                "label": "Night",
                "days_of_week": [1, 2, 3, 4, 5, 6, 7],
                "start_local_time": "18:00:00",
                "end_local_time": "23:00:00",
                "hourly_rate_rupees": "300.00",
            },
        )
    assert denied.status_code == 403
    with staff_client(db, "SUPER_ADMIN", "ps5-peak") as client:
        created = client.post(
            f"/pricing/plans/{plan.id}/schedules",
            json={
                "label": "PS5 peak",
                "days_of_week": [1, 2, 3, 4, 5, 6, 7],
                "start_local_time": "18:00:00",
                "end_local_time": "23:00:00",
                "hourly_rate_rupees": "300.00",
            },
        )
        assert created.status_code == 201, created.text
        schedule_id = created.json()["id"]
    cashier = create_user(
        db,
        username="package-desk",
        password=TEST_PASSWORD,
        display_name="Desk",
        role_name="CASHIER",
        actor=None,
    )
    play = start_session(
        db,
        station_code="PS5-01",
        staff=cashier,
        billing_mode=BillingMode.PREPAID,
        guest_label="Package guest",
        package_code="PS5-1H",
        payment_method=PaymentMethod.CASH,
        now=PEAK,
    )
    assert play.package_price_rupees == Decimal("250.00")
    assert play.hourly_rate_rupees == Decimal("300.00")
    with staff_client(db, "SUPER_ADMIN", "ps5-peak-off") as client:
        retired = client.post(f"/pricing/schedules/{schedule_id}/deactivate")
    assert retired.status_code == 200
    assert retired.json()["is_active"] is False


def test_customer_cannot_add_a_schedule(db) -> None:
    seed(db)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        registered = client.post(
            "/customers/register",
            json={
                "username": "no.peak",
                "password": "player-pass-1",
                "display_name": "No Peak",
                "mobile": "9876553333",
            },
        )
        token = registered.json()["access_token"]
        denied = client.post(
            "/pricing/plans/11111111-1111-4111-8111-111111111111/schedules",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "label": "Night",
                "days_of_week": [1],
                "start_local_time": "18:00:00",
                "end_local_time": "23:00:00",
                "hourly_rate_rupees": "200.00",
            },
        )
    finally:
        app.dependency_overrides.clear()
    assert denied.status_code == 401
