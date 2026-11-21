import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.seed import seed
from app.main import app
from app.models.enums import DeviceType, StationStatus
from app.models.pricing import Package, PriceChangeLog, PricingPlan, PricingSchedule
from app.models.station import Station
from app.db.session import get_db


def test_seed_creates_the_cafe_catalog(db) -> None:
    result = seed(db)

    assert result.stations_inserted == 21
    assert result.plans_inserted == 3
    assert result.packages_inserted == 3
    assert db.scalar(select(func.count()).select_from(Station)) == 21

    codes = set(db.scalars(select(Station.code)))
    assert codes == {f"PC-{index:02d}" for index in range(1, 16)} | {
        "PS5-01",
        "PS5-02",
        "PS5-03",
        "SIM-01",
        "SIM-02",
        "CASHIER-01",
    }

    cashier = db.scalar(select(Station).where(Station.code == "CASHIER-01"))
    assert cashier is not None
    assert cashier.device_type == DeviceType.ADMIN_WORKSTATION
    assert cashier.is_customer_station is False
    assert cashier.is_billable is False
    assert cashier.status == StationStatus.AVAILABLE

    rates = {
        plan.device_type: plan.hourly_rate_paise
        for plan in db.scalars(select(PricingPlan).where(PricingPlan.station_id.is_(None)))
    }
    assert rates == {
        DeviceType.PC: 15000,
        DeviceType.PS5: 25000,
        DeviceType.RACING_SIMULATOR: 80000,
    }
    assert db.scalar(select(func.count()).select_from(PricingPlan).where(PricingPlan.device_type == DeviceType.ADMIN_WORKSTATION)) == 0

    packages = {
        package.code: package.price_paise
        for package in db.scalars(select(Package))
    }
    assert packages == {"PS5-1H": 25000, "PS5-2H": 45000, "PS5-3H": 60000}
    assert db.scalar(select(func.count()).select_from(PricingSchedule)) == 0
    assert db.scalar(select(func.count()).select_from(PriceChangeLog)) == 6


def test_seed_again_does_not_change_an_edited_price(db) -> None:
    seed(db)
    plan = db.scalar(
        select(PricingPlan).where(
            PricingPlan.device_type == DeviceType.PC,
            PricingPlan.station_id.is_(None),
        )
    )
    assert plan is not None
    plan.hourly_rate_paise = 18000
    db.commit()

    second = seed(db)

    assert second.stations_inserted == 0
    assert second.plans_inserted == 0
    assert second.packages_inserted == 0
    db.refresh(plan)
    assert plan.hourly_rate_paise == 18000


def test_admin_workstation_cannot_be_billable(db) -> None:
    db.add(
        Station(
            code="CASHIER-99",
            display_name="Bad cashier",
            device_type=DeviceType.ADMIN_WORKSTATION,
            status=StationStatus.AVAILABLE,
            is_customer_station=False,
            is_billable=True,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_only_one_active_default_plan_per_device(db) -> None:
    seed(db)
    db.add(
        PricingPlan(
            name="Second PC default",
            device_type=DeviceType.PC,
            station_id=None,
            hourly_rate_paise=16000,
            billing_increment_seconds=60,
            minimum_duration_seconds=60,
            is_active=True,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_pricing_endpoint_reads_the_database(db) -> None:
    seed(db)
    plan = db.scalar(
        select(PricingPlan).where(
            PricingPlan.device_type == DeviceType.PS5,
            PricingPlan.station_id.is_(None),
        )
    )
    assert plan is not None
    plan.hourly_rate_paise = 27500
    db.commit()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).get("/pricing")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    ps5 = next(item for item in body["plans"] if item["device_type"] == "PS5" and item["station_id"] is None)
    assert ps5["hourly_rate_paise"] == 27500
    assert ps5["hourly_rate_inr"] == "275.00"
    assert body["schedule_count"] == 0


def test_station_list_marks_cashier_separately(db) -> None:
    seed(db)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).get("/stations")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    stations = response.json()
    assert len(stations) == 21
    cashier = next(item for item in stations if item["code"] == "CASHIER-01")
    assert cashier["is_billable"] is False
    assert cashier["is_customer_station"] is False
    assert all(item["is_billable"] for item in stations if item["code"] != "CASHIER-01")
