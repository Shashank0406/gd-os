from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.pricing import Package, PricingPlan, PricingSchedule
from app.schemas.catalog import CatalogOut

router = APIRouter(tags=["pricing"])


@router.get("/pricing", response_model=CatalogOut)
def get_pricing(db: Session = Depends(get_db)) -> CatalogOut:
    plans = list(db.scalars(select(PricingPlan).order_by(PricingPlan.device_type, PricingPlan.name)))
    packages = list(db.scalars(select(Package).order_by(Package.sort_order, Package.code)))
    schedule_count = db.scalar(select(func.count()).select_from(PricingSchedule)) or 0
    return CatalogOut(plans=plans, packages=packages, schedule_count=schedule_count)
