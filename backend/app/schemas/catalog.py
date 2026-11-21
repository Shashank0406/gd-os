import uuid

from pydantic import BaseModel, ConfigDict, computed_field

from app.models.enums import DeviceType, StationStatus
from app.schemas.money import format_inr


class StationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    display_name: str
    device_type: DeviceType
    status: StationStatus
    is_customer_station: bool
    is_billable: bool
    maintenance_reason: str | None


class PricingPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    device_type: DeviceType
    station_id: uuid.UUID | None
    hourly_rate_paise: int
    billing_increment_seconds: int
    minimum_duration_seconds: int
    is_active: bool

    @computed_field
    @property
    def hourly_rate_inr(self) -> str:
        return format_inr(self.hourly_rate_paise)


class PackageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    device_type: DeviceType
    duration_seconds: int
    price_paise: int
    is_active: bool
    sort_order: int

    @computed_field
    @property
    def price_inr(self) -> str:
        return format_inr(self.price_paise)


class CatalogOut(BaseModel):
    plans: list[PricingPlanOut]
    packages: list[PackageOut]
    schedule_count: int
