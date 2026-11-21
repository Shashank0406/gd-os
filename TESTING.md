# Testing

Evidence for the current milestone only. A passing health check is not production readiness.

## Passed

| Check | Result | Evidence |
|---|---|---|
| `GET /health` returns GD OS identity and a UTC timestamp | Passed on the Mac, 19 Nov 2026. | `backend/tests/test_health.py` |
| Docker Compose health on this Mac | Passed on 19 Nov 2026. | Local Docker Desktop 29.8. This does not prove a Windows reboot. |
| Catalog seed, cashier exclusion, single default price, edited price kept, pricing API reads the database | Passed on the Mac, 22 Nov 2026. `pytest`: 7 passed. | `backend/tests/test_catalog.py` against database `gdos_test` |
| Live API catalog after container start | Passed on the Mac, 22 Nov 2026. `/ready` connected. `/stations` returned 21 stations and `CASHIER-01` was not billable. | `docker compose up -d --build` |
| Prices stored and returned in rupees | Passed on the Mac, 22 Nov 2026. `pytest`: 7 passed. Live `/pricing` returned `150.00`, `250.00`, and `800.00`. Existing rows were converted by migration `0002_prices_in_rupees`. | `backend/tests/test_catalog.py` and `GET /pricing` |

## Not run

- Billing calculations
- Pricing snapshots
- Double-session prevention
- Server restart recovery
- Database restore
- Offline operation
- Windows agent disconnect and reconnect
- Physical diskless PC lock/unlock
- 8–12 hour stability

## How to run

From `backend/` with the virtualenv installed:

```bash
pytest
```

The health test uses FastAPI's in-process client. It does not need Docker or Windows.
