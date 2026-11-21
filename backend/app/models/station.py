import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import DeviceType, StationStatus


class Station(Base):
    __tablename__ = "stations"
    __table_args__ = (
        CheckConstraint(
            "device_type <> 'ADMIN_WORKSTATION' "
            "OR (is_customer_station = false AND is_billable = false)",
            name="ck_stations_admin_not_billable",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    device_type: Mapped[DeviceType] = mapped_column(
        Enum(DeviceType, native_enum=False, length=32),
        nullable=False,
    )
    status: Mapped[StationStatus] = mapped_column(
        Enum(StationStatus, native_enum=False, length=32),
        nullable=False,
        default=StationStatus.AVAILABLE,
        server_default=StationStatus.AVAILABLE.value,
    )
    is_customer_station: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_billable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    maintenance_reason: Mapped[str | None] = mapped_column(String(500))
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
