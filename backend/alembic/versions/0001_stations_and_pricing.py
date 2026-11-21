"""Stations, hourly plans, packages, and the price change log."""

from alembic import op
import sqlalchemy as sa

revision = "0001_stations_and_pricing"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("device_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="AVAILABLE", nullable=False),
        sa.Column("is_customer_station", sa.Boolean(), nullable=False),
        sa.Column("is_billable", sa.Boolean(), nullable=False),
        sa.Column("maintenance_reason", sa.String(length=500)),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "device_type <> 'ADMIN_WORKSTATION' "
            "OR (is_customer_station = false AND is_billable = false)",
            name="ck_stations_admin_not_billable",
        ),
        sa.UniqueConstraint("code", name="uq_stations_code"),
    )
    op.create_table(
        "pricing_plans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("device_type", sa.String(length=32), nullable=False),
        sa.Column("station_id", sa.Uuid(), sa.ForeignKey("stations.id")),
        sa.Column("hourly_rate_paise", sa.Integer(), nullable=False),
        sa.Column("billing_increment_seconds", sa.Integer(), nullable=False),
        sa.Column("minimum_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("hourly_rate_paise >= 0", name="ck_pricing_plans_rate_nonnegative"),
        sa.CheckConstraint("billing_increment_seconds > 0", name="ck_pricing_plans_increment_positive"),
        sa.CheckConstraint("minimum_duration_seconds >= 0", name="ck_pricing_plans_minimum_nonnegative"),
        sa.CheckConstraint("device_type <> 'ADMIN_WORKSTATION'", name="ck_pricing_plans_not_admin"),
    )
    op.create_index(
        "uq_pricing_plans_one_active_default_per_device",
        "pricing_plans",
        ["device_type"],
        unique=True,
        postgresql_where=sa.text("station_id IS NULL AND is_active"),
    )
    op.create_index(
        "uq_pricing_plans_one_override_per_station",
        "pricing_plans",
        ["station_id"],
        unique=True,
        postgresql_where=sa.text("station_id IS NOT NULL"),
    )
    op.create_table(
        "packages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("device_type", sa.String(length=32), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("price_paise", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("price_paise >= 0", name="ck_packages_price_nonnegative"),
        sa.CheckConstraint("duration_seconds > 0", name="ck_packages_duration_positive"),
        sa.CheckConstraint("device_type <> 'ADMIN_WORKSTATION'", name="ck_packages_not_admin"),
        sa.UniqueConstraint("code", name="uq_packages_code"),
    )
    op.create_table(
        "pricing_schedules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("pricing_plan_id", sa.Uuid(), sa.ForeignKey("pricing_plans.id"), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("days_of_week", sa.String(length=32), nullable=False),
        sa.Column("start_local_time", sa.Time(), nullable=False),
        sa.Column("end_local_time", sa.Time(), nullable=False),
        sa.Column("hourly_rate_paise", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("hourly_rate_paise >= 0", name="ck_pricing_schedules_rate_nonnegative"),
    )
    op.create_table(
        "price_change_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("old_value", sa.String(length=64)),
        sa.Column("new_value", sa.String(length=64), nullable=False),
        sa.Column("actor_label", sa.String(length=80)),
        sa.Column("note", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("price_change_log")
    op.drop_table("pricing_schedules")
    op.drop_table("packages")
    op.drop_index("uq_pricing_plans_one_override_per_station", table_name="pricing_plans")
    op.drop_index("uq_pricing_plans_one_active_default_per_device", table_name="pricing_plans")
    op.drop_table("pricing_plans")
    op.drop_table("stations")
