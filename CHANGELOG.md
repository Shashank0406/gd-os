# Changelog

## 0.6.0 — Cashier screen

- Staff sign in and see the floor. The cashier workstation cannot be billed.
- A session can be started for a guest, an existing customer, or a new walk-in.
- The screen shows the amount due from the server before cash, UPI, or card is taken.
- Prepaid time can be added from the same screen. The API stores the charge.

## 0.5.0 — Session and billing engine

- One session engine covers PCs, PS5s, and simulators.
- Postpaid, prepaid hourly, prepaid packages, and free play are calculated in rupees on the server clock.
- A running session keeps the price from when it started.
- A station and a customer can each have only one active session. The cashier workstation cannot be billed.
- Ending early does not refund a prepaid package. Time past the purchased block is billed from the saved hourly rate.

## 0.4.0 — Customer accounts

- Customers register and sign in with a username and password. There is no OTP login.
- Mobile numbers are stored as 10 digits so a cashier can find a customer.
- A cashier can register a walk-in without a password.
- A customer token cannot call staff routes, and a staff token cannot open the customer profile.

## 0.3.0 — Staff login and permissions

- Staff sign in with a username and an Argon2id password hash.
- Super admin, manager, and cashier roles are stored as permissions.
- Cashiers can read stations and prices. They cannot change a price or create staff.
- Price edits record the old and new rupee amounts and an audit row.
- Login failures are rate-limited, and the placeholder `JWT_SECRET` cannot issue a token.

## 0.2.1 — Prices stored in rupees

- Hourly rates and package prices are rupees with two decimal places. ₹150 is `150.00`.
- Existing paise amounts are divided by 100 during migration `0002_prices_in_rupees`.

## 0.2.0 — Station and price catalog

- Added the PostgreSQL catalog: stations, hourly plans, packages, optional schedules, and a price change log.
- Seeded PC-01–PC-15, PS5-01–PS5-03, SIM-01, SIM-02, and CASHIER-01.
- Stored default rates in the price tables. A second seed does not overwrite an edited rate.
- The database rejects a billable cashier station and a second active default plan for the same device type.

## 0.1.0 — Day 1 foundation

- Created the GD OS repository.
- Added Docker Compose for PostgreSQL 16 and the FastAPI service, using relative paths so the same file runs on macOS and Windows.
- Added `GET /health`.
- Documented that development is on Mac and the café host is Windows.
- No schema, billing, authentication, or Windows agent yet.
