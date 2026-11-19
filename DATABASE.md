# Database

PostgreSQL 16 is the system of record. It runs in Docker on the development Mac and on the café Windows server. The data directory is the named volume `gd_os_pgdata`, which survives a container restart.

No tables exist yet. Alembic migrations start on Day 2.

Planned tables:

- users, roles, permissions
- customers
- stations (PC, PS5, racing simulator, admin workstation)
- pricing plans, packages, price change log
- sessions, session extensions, reservations
- payments, receipts
- maintenance logs, audit logs, settings
- agent devices, agent commands

Day 2 will also seed PC-01 through PC-15, PS5-01 through PS5-03, SIM-01, SIM-02, and CASHIER-01. Default rates live in those rows, not in Python conditionals.

Billing timestamps will be `timestamptz` stored in UTC.
