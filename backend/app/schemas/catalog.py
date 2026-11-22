import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer

from app.models.enums import DeviceType, StationStatus
from app.schemas.money import rupees_text


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
    last_heartbeat_at: datetime | None = None
    agent_desired: str | None = None


class PricingPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    device_type: DeviceType
    station_id: uuid.UUID | None
    hourly_rate_rupees: Decimal
    billing_increment_seconds: int
    minimum_duration_seconds: int
    is_active: bool

    @field_serializer("hourly_rate_rupees")
    def serialize_hourly_rate(self, value: Decimal) -> str:
        return rupees_text(value)


class PackageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    device_type: DeviceType
    duration_seconds: int
    price_rupees: Decimal
    is_active: bool
    sort_order: int

    @field_serializer("price_rupees")
    def serialize_price(self, value: Decimal) -> str:
        return rupees_text(value)


class CatalogOut(BaseModel):
    plans: list[PricingPlanOut]
    packages: list[PackageOut]
    schedule_count: int
