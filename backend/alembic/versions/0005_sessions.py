"""Play sessions, extensions, and payments."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_sessions"
down_revision = "0004_customers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("station_id", sa.Uuid(), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column("customer_id", sa.Uuid(), sa.ForeignKey("customers.id")),
        sa.Column("guest_label", sa.String(length=80)),
        sa.Column("staff_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("billing_mode", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("hourly_rate_rupees", sa.Numeric(12, 2), nullable=False),
        sa.Column("billing_increment_seconds", sa.Integer(), nullable=False),
        sa.Column("minimum_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("purchased_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("package_code", sa.String(length=32)),
        sa.Column("package_price_rupees", sa.Numeric(12, 2)),
        sa.Column("final_amount_rupees", sa.Numeric(12, 2)),
        sa.Column("pricing_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("hourly_rate_rupees >= 0", name="ck_sessions_rate_nonnegative"),
        sa.CheckConstraint(
            "customer_id IS NOT NULL OR guest_label IS NOT NULL",
            name="ck_sessions_customer_or_guest",
        ),
    )
    op.create_index(
        "uq_sessions_one_active_per_station",
        "sessions",
        ["station_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "uq_sessions_one_active_per_customer",
        "sessions",
        ["customer_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND customer_id IS NOT NULL"),
    )
    op.create_table(
        "session_extensions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("added_seconds", sa.Integer(), nullable=False),
        sa.Column("amount_rupees", sa.Numeric(12, 2), nullable=False),
        sa.Column("staff_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("amount_rupees", sa.Numeric(12, 2), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("staff_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount_rupees >= 0", name="ck_payments_amount_nonnegative"),
    )


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("session_extensions")
    op.drop_index("uq_sessions_one_active_per_customer", table_name="sessions")
    op.drop_index("uq_sessions_one_active_per_station", table_name="sessions")
    op.drop_table("sessions")
