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

No other routes exist.
