# API documentation

Base URL in development: `http://localhost:8000`

## GET /health

Liveness probe. It does not check PostgreSQL yet.

Response `200`:

```json
{
  "status": "ok",
  "service": "gd-os",
  "product": "Gamers District Operating System",
  "time_utc": "2026-11-19T05:30:00+00:00"
}
```

`time_utc` is the server clock in UTC.

## GET /ready

Checks that PostgreSQL accepts a query.

```json
{"status": "ok", "database": "connected"}
```

## GET /stations

Returns the 21 seeded stations. `CASHIER-01` has `is_billable: false` and `is_customer_station: false`.

## GET /pricing

Returns hourly plans and packages from the database. Money is `hourly_rate_paise` or `price_paise`, plus a display string such as `"150.00"`. The display string is derived from paise.

These two routes do not require a staff login yet. Staff authentication is the next milestone. Do not expose the server beyond the café LAN.
