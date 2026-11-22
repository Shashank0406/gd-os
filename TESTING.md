# Testing

Evidence for the current milestone only. A passing health check is not production readiness.

## Passed

| Check | Result | Evidence |
|---|---|---|
| `GET /health` returns GD OS identity and a UTC timestamp | Passed on the Mac, 19 Nov 2026. | `backend/tests/test_health.py` |
| Docker Compose health on this Mac | Passed on 19 Nov 2026. | Local Docker Desktop 29.8. This does not prove a Windows reboot. |
| Catalog seed, cashier exclusion, single default price, edited price kept, pricing API reads the database | Passed on the Mac, 22 Nov 2026. `pytest`: 7 passed. | `backend/tests/test_catalog.py` against database `gdos_test` |
| Live API catalog after container start | Passed on the Mac, 22 Nov 2026. `/ready` connected. `/stations` returned 21 stations and `CASHIER-01` was not billable. | `docker compose up -d --build` |
| Prices stored and returned in rupees | Passed on the Mac, 22 Nov 2026. Live `/pricing` returned `150.00`, `250.00`, and `800.00`. Existing rows were converted by migration `0002_prices_in_rupees`. | `backend/tests/test_catalog.py` and `GET /pricing` |
| Staff login, hashed passwords, cashier price block, admin price audit, manager staff block, rate limit, placeholder JWT secret | Passed on the Mac, 22 Nov 2026. `pytest`: 16 passed. | `backend/tests/test_auth.py` |
| Customer register, login, duplicate mobile, cashier walk-in search, customer and staff tokens stay separate | Passed on the Mac, 22 Nov 2026. `pytest`: 20 passed. | `backend/tests/test_customers.py` |
| Billing rounding, price snapshot, double start, cashier station, package overtime, prepaid extension, free play, one customer per session, API minimum charge | Passed on the Mac, 22 Nov 2026. `pytest`: 34 passed. | `backend/tests/test_billing.py`, `backend/tests/test_sessions.py` |
| Live API postpaid start and immediate end on PC-15 | Passed on the Mac, 22 Nov 2026. Saved rate `150.00`, local offset `+05:30`, final and paid `2.50`. | Docker API on `http://localhost:8000` |
| Amount due before a session ends | Passed on the Mac, 22 Nov 2026. `pytest`: 35 passed. | `backend/tests/test_sessions.py` |
| Cashier screen money preview | Passed on the Mac, 22 Nov 2026. `npm test`: 4 passed. | `frontend/src/money.test.js` |
| Cashier screen: sign in, postpaid start, extend, end and take ₹2.50; prepaid hour shows due now ₹150.00 and early end keeps the paid amount | Passed on the Mac, 22 Nov 2026, in the browser at `http://localhost:8000`. `CASHIER-01` stays disabled. | Cashier screen served by the API |
| Agent pairing, heartbeat lock, unlock only during a session, cashier blocked from pairing, mismatched MAC and hardware id | Passed on the Mac, 22 Nov 2026. `pytest`: 39 passed. | `backend/tests/test_agent.py` |
| Cashier floor and Mac simulator for PC-01: No agent, then Lock, Unlock while a session is open, Lock again after payment | Passed on the Mac, 22 Nov 2026. The simulator printed `PC-01 LOCK`, then `PC-01 UNLOCK`, then `PC-01 LOCK`. This does not lock a Windows PC. | `http://localhost:8000` and `agent/simulator.py` |
| Takings follow the Kolkata midnight, split cash and UPI, and reject a customer token | Passed on the Mac, 22 Nov 2026. `pytest`: 41 passed. | `backend/tests/test_reports.py` |
| Cashier floor today total rises when a session is paid | Passed on the Mac, 22 Nov 2026. The floor moved from `Today ₹157.50` to `Today ₹160.00` after a ₹2.50 cash payment on PC-03. | `http://localhost:8000` |
| Backup, refused restore, and restore into a separate database | Passed on the Mac, 22 Nov 2026. The copy had 21 stations and the PC rate `150.00`. The live database was not replaced. | `scripts/test_backup.sh` |
| Reservation overlap, future hold does not block play now, cashier station rejected, customer token rejected, start consumes the hold | Passed on the Mac, 22 Nov 2026. `pytest`: 44 passed. | `backend/tests/test_reservations.py` |
| Cashier reserves PC-14, a second hold is rejected, then the session starts from that hold and is closed | Passed on the Mac, 22 Nov 2026. The screen showed "Reserved now for Hold check" and "already reserved", then the session closed. | `http://localhost:8000` |
| Closed session receipt, open session rejected, customer token rejected | Passed on the Mac, 22 Nov 2026. `pytest`: 46 passed. | `backend/tests/test_receipts.py` |
| Cashier screen shows the receipt after closing PC-13 | Passed on the Mac, 22 Nov 2026. The panel showed Receipt, Receipt check, cash ₹2.50, and the final ₹2.50. PC-13 was free again. | `http://localhost:8000` |

## Not run

- Billing calculations
- Pricing snapshots
- Double-session prevention
- Server restart recovery
- Database restore
- Offline operation
- Physical diskless PC lock/unlock
- 8–12 hour stability

## How to run

From `backend/` with the virtualenv installed:

```bash
pytest
```

The health test uses FastAPI's in-process client. It does not need Docker or Windows.
| Live staff login | Passed on the Mac, 22 Nov 2026. `/pricing` without a token returned 401. Login as `admin` returned `SUPER_ADMIN`. The same token read the PC rate `150.00`. |
| Live customer registration | Passed on the Mac, 22 Nov 2026. `POST /customers/register` returned 201. `GET /customers/me` returned mobile `9988776655`. `POST /customers/otp/request` returned 404. |
