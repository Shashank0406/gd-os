# Testing

Evidence for the current milestone only. A passing health check is not production readiness.

## Passed

| Check | Result | Evidence |
|---|---|---|
| `GET /health` returns GD OS identity and a UTC timestamp | Passed on the Mac, 19 Nov 2026. `pytest`: 1 passed. | `backend/tests/test_health.py` |
| Docker Compose health on this Mac | Passed. `curl http://localhost:8000/health` returned `status: ok` after `docker compose up -d --build`. PostgreSQL reported healthy. | Local Docker Desktop 29.8. This does not prove a Windows reboot. |

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
