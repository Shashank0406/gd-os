"""Rupee amounts use two decimal places and decimal arithmetic, never binary floats."""

from decimal import Decimal, ROUND_HALF_UP

RUPEE = Decimal("0.01")


def rupees(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(RUPEE, rounding=ROUND_HALF_UP)


def rupees_text(value: Decimal) -> str:
    return f"{rupees(value):.2f}"
