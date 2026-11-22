"""Station reservations. Scheduled bookings on one station cannot overlap."""

from alembic import op
import sqlalchemy as sa

revision = "0007_reservations"
down_revision = "0006_station_agents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.create_table(
        "reservations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("station_id", sa.Uuid(), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column("customer_id", sa.Uuid(), sa.ForeignKey("customers.id")),
        sa.Column("guest_label", sa.String(length=80)),
        sa.Column("staff_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id")),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("ends_at > starts_at", name="ck_reservations_end_after_start"),
        sa.CheckConstraint(
            "customer_id IS NOT NULL OR guest_label IS NOT NULL",
            name="ck_reservations_customer_or_guest",
        ),
    )
    op.execute(
        """
        ALTER TABLE reservations ADD CONSTRAINT ex_reservations_no_overlap
        EXCLUDE USING gist (
            station_id WITH =,
            tstzrange(starts_at, ends_at, '[)') WITH &&
        )
        WHERE (status = 'SCHEDULED')
        """
    )


def downgrade() -> None:
    op.drop_table("reservations")
