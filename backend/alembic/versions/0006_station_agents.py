"""Pair diskless PCs by MAC address and hardware id."""

from alembic import op
import sqlalchemy as sa

revision = "0006_station_agents"
down_revision = "0005_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "station_agents",
        sa.Column("station_id", sa.Uuid(), sa.ForeignKey("stations.id"), primary_key=True),
        sa.Column("mac_address", sa.String(length=17), nullable=False),
        sa.Column("hardware_uuid", sa.String(length=36), nullable=False),
        sa.Column("paired_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("paired_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("mac_address", name="uq_station_agents_mac"),
        sa.UniqueConstraint("hardware_uuid", name="uq_station_agents_hardware"),
        sa.CheckConstraint(
            "mac_address ~ '^([0-9a-f]{2}:){5}[0-9a-f]{2}$'",
            name="ck_station_agents_mac",
        ),
        sa.CheckConstraint(
            "hardware_uuid ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="ck_station_agents_hardware",
        ),
    )


def downgrade() -> None:
    op.drop_table("station_agents")
