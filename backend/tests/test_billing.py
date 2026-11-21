from decimal import Decimal

import pytest

from app.services.billing import (
    charge_rupees,
    extension_seconds,
    overtime_seconds,
    postpaid_billable_seconds,
    prepaid_purchase_seconds,
)


def test_full_hour_stays_exact() -> None:
    assert charge_rupees(Decimal("250.00"), 3600) == Decimal("250.00")
    assert charge_rupees(Decimal("150.00"), 3600) == Decimal("150.00")
    assert charge_rupees(Decimal("800.00"), 3600) == Decimal("800.00")


def test_one_minute_rounds_half_up() -> None:
    assert postpaid_billable_seconds(1, 60, 60) == 60
    assert charge_rupees(Decimal("250.00"), 60) == Decimal("4.17")
    assert charge_rupees(Decimal("150.00"), 60) == Decimal("2.50")
    assert charge_rupees(Decimal("800.00"), 60) == Decimal("13.33")


def test_minimum_duration_applies_to_a_short_postpaid_visit() -> None:
    assert postpaid_billable_seconds(0, 60, 60) == 60
    assert postpaid_billable_seconds(3601, 60, 60) == 3660


def test_prepaid_purchase_and_overtime_use_the_increment() -> None:
    assert prepaid_purchase_seconds(3600, 60, 60) == 3600
    assert extension_seconds(1800, 60) == 1800
    assert overtime_seconds(3601, 3600, 60) == 60
    assert overtime_seconds(1800, 3600, 60) == 0


def test_negative_time_is_rejected() -> None:
    with pytest.raises(ValueError):
        charge_rupees(Decimal("150.00"), -1)
