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

## POST /auth/login

Staff username and password. Returns a bearer token. The password is checked with Argon2id. Unknown users and wrong passwords return the same `401` message. After 5 failures from the same address within 5 minutes, the route returns `429`.

`JWT_SECRET` must be set to a value other than `change-me`. A shift token lasts 12 hours.

## POST /customers/register

Public on the café LAN. Body: `username`, `password`, `display_name`, `mobile`. The password is hashed with Argon2id. The response includes a customer token. There is no OTP route.

## POST /customers/login

Username and password. A walk-in with no password cannot sign in. Unknown users and wrong passwords return the same `401`.

## GET /customers/me

Requires a customer token. A staff token is rejected.

## POST /customers

Requires `customers.write`. A cashier registers a walk-in with `display_name` and `mobile`. Username and password are optional.

## GET /customers/search?mobile=

Requires `customers.read`. Accepts `9876543210` or `+91 9876543210` and returns the matching customer.

## POST /sessions

Requires `sessions.operate`. Starts a session on an available customer station. `CASHIER-01` is rejected. `billing_mode` is `POSTPAID`, `PREPAID`, or `FREE_PLAY`. Prepaid hourly needs `duration_seconds` and a payment method. A package needs `package_code`. The response includes the saved hourly rate and the start time in UTC and Asia/Kolkata.

## GET /sessions/{id}/due

Requires `sessions.read`. Returns the current bill, the amount already paid, and the balance still to collect. This does not close the session. Times use the server clock. The local time is Asia/Kolkata.

## POST /sessions/{id}/extend

Adds time. A prepaid extension is charged immediately from the saved hourly rate. A postpaid extension only moves the planned end.

## POST /sessions/{id}/end

Closes the session using the server clock. The final rupee amount uses the price saved at the start. The balance is recorded as cash, UPI, or card.

## GET /sessions/active

Requires `sessions.read`. Lists sessions that are still open.

## POST /stations/{code}/agent

Requires `stations.manage`. A manager pairs a gaming PC. PS5s, simulators, and `CASHIER-01` are rejected. The MAC address and hardware id must not already belong to another station.

## POST /agent/heartbeat

No staff token. The body is the PC's MAC address and hardware id. The response is `LOCK` or `UNLOCK`. `UNLOCK` means that station has an active session. A PC cannot send the amount to charge or the action it wants.

## GET /reports/takings

Requires `sessions.read`. Optional `date` is `YYYY-MM-DD`. When it is omitted, the date is today in Asia/Kolkata. The total is the sum of payments recorded on that local day. A payment just before midnight stays on that day, and one at midnight belongs to the next day.

## GET /stations

Requires a staff token with `stations.read`. Returns the 21 seeded stations. `CASHIER-01` has `is_billable: false` and `is_customer_station: false`.

## GET /pricing

Requires `pricing.read`. `hourly_rate_rupees` and `price_rupees` are rupee strings with two decimal places, such as `"150.00"`.

## PATCH /pricing/plans/{id}

Requires `pricing.write`. Body: `{"hourly_rate_rupees": "180.00"}`. The previous and new rupee amounts are stored in `price_change_log` and `audit_logs`. A cashier token receives `403`.

## POST /staff

Requires `staff.write`, which only the super admin role has. Creates a manager or cashier. Only a super admin can create another super admin. The response does not include the password.

## GET /audit

Requires `audit.read`. Super admins and managers can read it. Cashiers cannot.
