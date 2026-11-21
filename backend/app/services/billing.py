"""Session charges in rupees. The server clock supplies the elapsed time."""

from decimal import Decimal

from app.schemas.money import rupees


def round_up_seconds(elapsed_seconds: int, increment_seconds: int) -> int:
    if elapsed_seconds < 0:
        raise ValueError("Elapsed time cannot be negative")
    if increment_seconds <= 0:
        raise ValueError("Billing increment must be positive")
    if elapsed_seconds == 0:
        return 0
    return ((elapsed_seconds + increment_seconds - 1) // increment_seconds) * increment_seconds


def postpaid_billable_seconds(elapsed_seconds: int, increment_seconds: int, minimum_seconds: int) -> int:
    rounded = round_up_seconds(elapsed_seconds, increment_seconds)
    return max(rounded, minimum_seconds)


def prepaid_purchase_seconds(requested_seconds: int, increment_seconds: int, minimum_seconds: int) -> int:
    if requested_seconds <= 0:
        raise ValueError("Duration must be positive")
    return max(round_up_seconds(requested_seconds, increment_seconds), minimum_seconds)


def extension_seconds(requested_seconds: int, increment_seconds: int) -> int:
    if requested_seconds <= 0:
        raise ValueError("Extension must be positive")
    return round_up_seconds(requested_seconds, increment_seconds)


def overtime_seconds(elapsed_seconds: int, purchased_seconds: int, increment_seconds: int) -> int:
    extra = elapsed_seconds - purchased_seconds
    if extra <= 0:
        return 0
    return round_up_seconds(extra, increment_seconds)


def charge_rupees(hourly_rate_rupees: Decimal, seconds: int) -> Decimal:
    if seconds < 0:
        raise ValueError("Seconds cannot be negative")
    amount = (rupees(hourly_rate_rupees) * Decimal(seconds)) / Decimal(3600)
    return rupees(amount)
