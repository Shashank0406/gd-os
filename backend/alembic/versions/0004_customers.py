"""Customer accounts. Login is username and password. There is no OTP flow."""

from alembic import op
import sqlalchemy as sa

revision = "0004_customers"
down_revision = "0003_staff_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("username", sa.String(length=32)),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("mobile", sa.String(length=10), nullable=False),
        sa.Column("password_hash", sa.String(length=255)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("username", name="uq_customers_username"),
        sa.UniqueConstraint("mobile", name="uq_customers_mobile"),
        sa.CheckConstraint("mobile ~ '^[6-9][0-9]{9}$'", name="ck_customers_mobile"),
    )


def downgrade() -> None:
    op.drop_table("customers")
