import uuid
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import DeviceType


class PricingPlan(Base):
    """Hourly rate for a device type, or for one station when station_id is set."""

    __tablename__ = "pricing_plans"
    __table_args__ = (
        CheckConstraint("hourly_rate_paise >= 0", name="ck_pricing_plans_rate_nonnegative"),
        CheckConstraint(
            "billing_increment_seconds > 0",
            name="ck_pricing_plans_increment_positive",
        ),
        CheckConstraint(
            "minimum_duration_seconds >= 0",
            name="ck_pricing_plans_minimum_nonnegative",
        ),
        CheckConstraint(
            "device_type <> 'ADMIN_WORKSTATION'",
            name="ck_pricing_plans_not_admin",
        ),
        Index(
            "uq_pricing_plans_one_active_default_per_device",
            "device_type",
            unique=True,
            postgresql_where=text("station_id IS NULL AND is_active"),
        ),
        Index(
            "uq_pricing_plans_one_override_per_station",
            "station_id",
            unique=True,
            postgresql_where=text("station_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    device_type: Mapped[DeviceType] = mapped_column(
        Enum(DeviceType, native_enum=False, length=32),
        nullable=False,
    )
    station_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stations.id"))
    hourly_rate_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    billing_increment_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Package(Base):
    __tablename__ = "packages"
    __table_args__ = (
        CheckConstraint("price_paise >= 0", name="ck_packages_price_nonnegative"),
        CheckConstraint("duration_seconds > 0", name="ck_packages_duration_positive"),
        CheckConstraint("device_type <> 'ADMIN_WORKSTATION'", name="ck_packages_not_admin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    device_type: Mapped[DeviceType] = mapped_column(
        Enum(DeviceType, native_enum=False, length=32),
        nullable=False,
    )
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    price_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class PricingSchedule(Base):
    """Optional peak, off-peak, weekday, or weekend rate for a plan. Empty until an admin adds one."""

    __tablename__ = "pricing_schedules"
    __table_args__ = (
        CheckConstraint("hourly_rate_paise >= 0", name="ck_pricing_schedules_rate_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    pricing_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pricing_plans.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    days_of_week: Mapped[str] = mapped_column(String(32), nullable=False)
    start_local_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_local_time: Mapped[time] = mapped_column(Time, nullable=False)
    hourly_rate_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class PriceChangeLog(Base):
    __tablename__ = "price_change_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(64))
    new_value: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_label: Mapped[str | None] = mapped_column(String(80))
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
