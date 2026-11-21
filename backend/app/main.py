from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.pricing import router as pricing_router
from app.api.stations import router as stations_router
from app.core.config import get_settings
from app.db.session import get_db

settings = get_settings()

app = FastAPI(
    title="GD OS",
    summary="Gamers District Operating System",
    version="0.2.0",
)
app.include_router(stations_router)
app.include_router(pricing_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Process liveness. This does not check PostgreSQL."""
    return {
        "status": "ok",
        "service": settings.service_name,
        "product": settings.product_name,
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    """Database readiness. Billing data is readable when this returns ok."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
