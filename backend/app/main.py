from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.agent import router as agent_router
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.customers import router as customers_router
from app.api.pricing import router as pricing_router
from app.api.reservations import router as reservations_router
from app.api.reports import router as reports_router
from app.api.sessions import router as sessions_router
from app.api.staff import router as staff_router
from app.api.stations import router as stations_router
from app.core.config import get_settings
from app.db.session import get_db

settings = get_settings()

app = FastAPI(
    title="GD OS",
    summary="Gamers District Operating System",
    version="0.12.0",
)
app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(sessions_router)
app.include_router(staff_router)
app.include_router(audit_router)
app.include_router(stations_router)
app.include_router(agent_router)
app.include_router(pricing_router)
app.include_router(reports_router)
app.include_router(reservations_router)


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


def _cashier_static_dir() -> Path | None:
    for candidate in (Path("/app/static"), Path(__file__).resolve().parents[2] / "static"):
        if (candidate / "index.html").is_file():
            return candidate
    return None


_cashier_static = _cashier_static_dir()
if _cashier_static is not None:
    _assets = _cashier_static / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets), name="cashier-assets")

    @app.get("/", include_in_schema=False)
    def cashier_app() -> FileResponse:
        return FileResponse(_cashier_static / "index.html")
