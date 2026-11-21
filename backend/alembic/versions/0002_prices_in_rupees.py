"""Convert stored prices from paise integers to rupees with two decimal places."""

from alembic import op
import sqlalchemy as sa

revision = "0002_prices_in_rupees"
down_revision = "0001_stations_and_pricing"
branch_labels = None
depends_on = None


def _convert_amount(table: str, old_name: str, new_name: str, constraint: str) -> None:
    op.add_column(table, sa.Column(new_name, sa.Numeric(12, 2)))
    op.execute(f"UPDATE {table} SET {new_name} = ROUND({old_name} / 100.0, 2)")
    op.alter_column(table, new_name, nullable=False)
    op.drop_constraint(constraint, table, type_="check")
    op.drop_column(table, old_name)
    op.create_check_constraint(constraint, table, f"{new_name} >= 0")


def upgrade() -> None:
    _convert_amount(
        "pricing_plans",
        "hourly_rate_paise",
        "hourly_rate_rupees",
        "ck_pricing_plans_rate_nonnegative",
    )
    _convert_amount(
        "packages",
        "price_paise",
        "price_rupees",
        "ck_packages_price_nonnegative",
    )
    _convert_amount(
        "pricing_schedules",
        "hourly_rate_paise",
        "hourly_rate_rupees",
        "ck_pricing_schedules_rate_nonnegative",
    )
    op.execute(
        """
        UPDATE price_change_log
        SET field_name = 'hourly_rate_rupees',
            new_value = to_char(ROUND(new_value::numeric / 100, 2), 'FM999999990.00'),
            old_value = CASE
                WHEN old_value IS NULL THEN NULL
                ELSE to_char(ROUND(old_value::numeric / 100, 2), 'FM999999990.00')
            END
        WHERE field_name = 'hourly_rate_paise'
        """
    )
    op.execute(
        """
        UPDATE price_change_log
        SET field_name = 'price_rupees',
            new_value = to_char(ROUND(new_value::numeric / 100, 2), 'FM999999990.00'),
            old_value = CASE
                WHEN old_value IS NULL THEN NULL
                ELSE to_char(ROUND(old_value::numeric / 100, 2), 'FM999999990.00')
            END
        WHERE field_name = 'price_paise'
        """
    )


def downgrade() -> None:
    raise NotImplementedError("Rupee amounts are not converted back to paise.")
