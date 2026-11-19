from datetime import datetime, timezone

from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="GD OS",
    summary="Gamers District Operating System",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness for the local café server. This does not check PostgreSQL yet."""
    return {
        "status": "ok",
        "service": settings.service_name,
        "product": settings.product_name,
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }
