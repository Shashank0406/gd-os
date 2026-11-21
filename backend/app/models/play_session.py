import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import BillingMode, PaymentMethod, SessionStatus


class PlaySession(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint("hourly_rate_rupees >= 0", name="ck_sessions_rate_nonnegative"),
        CheckConstraint(
            "customer_id IS NOT NULL OR guest_label IS NOT NULL",
            name="ck_sessions_customer_or_guest",
        ),
        Index(
            "uq_sessions_one_active_per_station",
            "station_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index(
            "uq_sessions_one_active_per_customer",
            "customer_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE' AND customer_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    station_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stations.id"), nullable=False)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"))
    guest_label: Mapped[str | None] = mapped_column(String(80))
    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus, native_enum=False, length=16), nullable=False)
    billing_mode: Mapped[BillingMode] = mapped_column(Enum(BillingMode, native_enum=False, length=16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hourly_rate_rupees: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    billing_increment_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    purchased_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    package_code: Mapped[str | None] = mapped_column(String(32))
    package_price_rupees: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    final_amount_rupees: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    pricing_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SessionExtension(Base):
    __tablename__ = "session_extensions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    added_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_rupees: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount_rupees >= 0", name="ck_payments_amount_nonnegative"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    amount_rupees: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, native_enum=False, length=16), nullable=False)
    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
