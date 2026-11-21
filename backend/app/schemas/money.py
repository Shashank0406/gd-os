def format_inr(paise: int) -> str:
    """Format integer paise as a rupee string. 15000 becomes 150.00."""
    sign = "-" if paise < 0 else ""
    amount = abs(paise)
    return f"{sign}{amount // 100}.{amount % 100:02d}"
