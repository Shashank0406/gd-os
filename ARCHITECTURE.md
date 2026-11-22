# Architecture

## Runtime decision

GD OS is developed on a Mac and deployed on a Windows machine on the café LAN.

The server is a Linux container image (`python:3.12-slim` and `postgres:16`), started by Docker Compose. That image is built the same way on macOS and on Windows. Application code uses relative paths, UTC timestamps, and environment variables. It does not call macOS-only APIs.

The cashier screen is a browser application served with the API. On launch day it opens on Windows. During development it opens on the Mac against the same API. The admin screens are not built yet.

The gaming-PC agent is a Windows service. It is compiled for `win-x64` and is not part of the Docker stack. A simulator will exercise the agent protocol before any diskless PC is touched.

CCBoot remains responsible for PXE, disk images, and write-back. GD OS starts after Windows has booted.

## Process map

```
Cashier browser (Windows)  --LAN-->  GD OS API (Docker on the Windows server)
Admin browser              --LAN-->  GD OS API
Customer / PC UI           --LAN-->  GD OS API
Windows agent on PC-01..15 --LAN-->  GD OS API
GD OS API                  ------->  PostgreSQL (Docker volume)
CCBoot                     ------->  diskless boot only
```

PS5 consoles and racing simulators have no agent. Staff start and end those sessions from the cashier UI. The software does not power them off.

## Money and time

Money is stored in rupees with two decimal places (`numeric(12,2)`). ₹150 is `150.00`. Decimal arithmetic is used so amounts are not binary floats. A session copies the hourly rate, increment, minimum, and package price at start.

- A price edit affects new sessions only.
- `started_at` and `ended_at` come from the server clock in UTC.
- Screens show Asia/Kolkata.
- Postpaid amount is computed once at the end: round elapsed time up to the billing increment, apply the minimum duration, then round half-up to `0.01` rupee.
- A prepaid package is charged at its saved price. Ending early does not refund it. Time beyond the package is charged from the saved hourly rate.

## Station rule

`CASHIER-01` is an admin workstation. It is not a billable gaming station and is excluded from utilisation.

## Boundaries for later modules

Sessions, payments, stations, and audit logs are the core. Food and beverage can attach a future order to a session id without changing the billing formula.

The server identifies a diskless PC by MAC and hardware id on every heartbeat, because a shared CCBoot image cannot store a unique secret per PC and write-back is discarded on reboot. The server returns lock or unlock. An active session is the only unlock. Lock and unlock on a physical PC stay unverified until one diskless PC test passes.
