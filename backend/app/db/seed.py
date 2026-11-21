"""Initial café catalog.

These numbers are inserted into PostgreSQL once. Billing and the API read the
tables, not this module. Running the seed again inserts rows that are missing
and leaves existing prices unchanged.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import DeviceType, StationStatus
from app.models.pricing import Package, PriceChangeLog, PricingPlan
from app.models.station import Station

SEED_ACTOR = "system-seed"
DEFAULT_INCREMENT_SECONDS = 60
DEFAULT_MINIMUM_SECONDS = 60

STATIONS: tuple[tuple[str, str, DeviceType, bool, bool], ...] = tuple(
    [(f"PC-{index:02d}", f"PC {index:02d}", DeviceType.PC, True, True) for index in range(1, 16)]
    + [
        ("PS5-01", "PS5 01", DeviceType.PS5, True, True),
        ("PS5-02", "PS5 02", DeviceType.PS5, True, True),
        ("PS5-03", "PS5 03", DeviceType.PS5, True, True),
        ("SIM-01", "Simulator 01", DeviceType.RACING_SIMULATOR, True, True),
        ("SIM-02", "Simulator 02", DeviceType.RACING_SIMULATOR, True, True),
        ("CASHIER-01", "Cashier 01", DeviceType.ADMIN_WORKSTATION, False, False),
    ]
)

# hourly_rate_paise: ₹150, ₹250, and ₹800.
DEFAULT_PLANS: tuple[tuple[str, DeviceType, int], ...] = (
    ("Gaming PC default", DeviceType.PC, 15000),
    ("PS5 default", DeviceType.PS5, 25000),
    ("Racing simulator default", DeviceType.RACING_SIMULATOR, 80000),
)

# price_paise: ₹250, ₹450, and ₹600.
PACKAGES: tuple[tuple[str, str, DeviceType, int, int, int], ...] = (
    ("PS5-1H", "PS5 1 hour", DeviceType.PS5, 3600, 25000, 1),
    ("PS5-2H", "PS5 2 hours", DeviceType.PS5, 7200, 45000, 2),
    ("PS5-3H", "PS5 3 hours", DeviceType.PS5, 10800, 60000, 3),
)


@dataclass(frozen=True)
class SeedResult:
    stations_inserted: int
    plans_inserted: int
    packages_inserted: int


def seed(session: Session) -> SeedResult:
    stations_inserted = _seed_stations(session)
    plans_inserted = _seed_plans(session)
    packages_inserted = _seed_packages(session)
    session.commit()
    return SeedResult(stations_inserted, plans_inserted, packages_inserted)


def _seed_stations(session: Session) -> int:
    inserted = 0
    for code, display_name, device_type, is_customer, is_billable in STATIONS:
        exists = session.scalar(select(Station.id).where(Station.code == code))
        if exists is not None:
            continue
        session.add(
            Station(
                code=code,
                display_name=display_name,
                device_type=device_type,
                status=StationStatus.AVAILABLE,
                is_customer_station=is_customer,
                is_billable=is_billable,
            )
        )
        inserted += 1
    session.flush()
    return inserted


def _seed_plans(session: Session) -> int:
    inserted = 0
    for name, device_type, hourly_rate_paise in DEFAULT_PLANS:
        exists = session.scalar(
            select(PricingPlan.id).where(
                PricingPlan.device_type == device_type,
                PricingPlan.station_id.is_(None),
            )
        )
        if exists is not None:
            continue
        plan = PricingPlan(
            name=name,
            device_type=device_type,
            station_id=None,
            hourly_rate_paise=hourly_rate_paise,
            billing_increment_seconds=DEFAULT_INCREMENT_SECONDS,
            minimum_duration_seconds=DEFAULT_MINIMUM_SECONDS,
            is_active=True,
        )
        session.add(plan)
        session.flush()
        _log_initial_price(session, "pricing_plan", plan.id, "hourly_rate_paise", hourly_rate_paise)
        inserted += 1
    return inserted


def _seed_packages(session: Session) -> int:
    inserted = 0
    for code, name, device_type, duration_seconds, price_paise, sort_order in PACKAGES:
        exists = session.scalar(select(Package.id).where(Package.code == code))
        if exists is not None:
            continue
        package = Package(
            code=code,
            name=name,
            device_type=device_type,
            duration_seconds=duration_seconds,
            price_paise=price_paise,
            is_active=True,
            sort_order=sort_order,
        )
        session.add(package)
        session.flush()
        _log_initial_price(session, "package", package.id, "price_paise", price_paise)
        inserted += 1
    return inserted


def _log_initial_price(session: Session, entity_type: str, entity_id, field_name: str, value: int) -> None:
    session.add(
        PriceChangeLog(
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            old_value=None,
            new_value=str(value),
            actor_label=SEED_ACTOR,
            note="initial catalog",
        )
    )


def main() -> None:
    from app.db.session import get_session_factory

    with get_session_factory()() as session:
        result = seed(session)
    print(
        "seed complete "
        f"stations={result.stations_inserted} "
        f"plans={result.plans_inserted} "
        f"packages={result.packages_inserted}"
    )


if __name__ == "__main__":
    main()
