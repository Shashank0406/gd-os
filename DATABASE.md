# Database

PostgreSQL 16 is the system of record. It runs in Docker on the development Mac and on the café Windows server. The data directory is the named volume `gd_os_pgdata`, which survives a container restart.

The API container runs `alembic upgrade head` and the seed on startup.

Migrations:

- `0001_stations_and_pricing` creates the catalog tables.
- `0002_prices_in_rupees` stores amounts as rupees.
- `0003_staff_auth` adds roles, permissions, users, and audit logs.

Tables in this migration:

- `stations`
- `pricing_plans`
- `packages`
- `pricing_schedules` (empty until an admin adds peak, off-peak, weekday, or weekend rates)
- `price_change_log`

Amounts are `numeric(12,2)` rupees. Seeded once, and not overwritten if you run the seed again:

| Code | Type | Billable | Default hourly rate |
|---|---|---|---|
| PC-01 … PC-15 | PC | yes | ₹150.00 |
| PS5-01 … PS5-03 | PS5 | yes | ₹250.00 |
| SIM-01, SIM-02 | Racing simulator | yes | ₹800.00 |
| CASHIER-01 | Admin workstation | no | none |

PS5 packages: 1 hour ₹250, 2 hours ₹450, 3 hours ₹600. The seeded billing increment and minimum duration are 60 seconds. Those are rows, so a later admin screen can change them.

`CASHIER-01` fails a database check if it is marked billable or as a customer station. A pricing plan cannot use the admin workstation device type. Each device type has one active default plan. A station may have one override plan.

Staff roles are `SUPER_ADMIN`, `MANAGER`, and `CASHIER`. A user has one role. Permissions are rows, so a manager can read staff and audit records without changing prices.

Still to add: customers, sessions, payments, receipts, maintenance, and agent tables. Session timestamps will be `timestamptz` in UTC.
