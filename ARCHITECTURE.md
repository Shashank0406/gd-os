# Architecture

## Runtime decision

GD OS is developed on a Mac and deployed on a Windows machine on the café LAN.

The server is a Linux container image (`python:3.12-slim` and `postgres:16`), started by Docker Compose. That image is built the same way on macOS and on Windows. Application code uses relative paths, UTC timestamps, and environment variables. It does not call macOS-only APIs.

The cashier and admin interfaces are browser applications. On launch day they open on Windows. During development they open on the Mac against the same API.

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

Money is stored as integer paise. ₹150 is `15000`. The catalog tables and seed are in place. Session snapshots and the charge calculation are not built yet.

- Money is integer paise. ₹150 is `15000`.
- Session start copies the active price into an immutable snapshot.
- A price edit affects new sessions only.
- `started_at` and `ended_at` come from the server clock in UTC.
- Screens show Asia/Kolkata.
- Postpaid amount is computed once at the end: round elapsed time up to the billing increment, apply the minimum duration, then `(hourly_rate_paise * billable_seconds + 1800) // 3600`.

## Station rule

`CASHIER-01` is an admin workstation. It is not a billable gaming station and is excluded from utilisation.

## Boundaries for later modules

Sessions, payments, stations, and audit logs are the core. Food and beverage can attach a future order to a session id without changing the billing formula.

The Windows agent identifies a diskless PC by MAC and hardware id on every boot, because a shared CCBoot image cannot store a unique secret per PC and write-back is discarded on reboot. Lock and unlock stay unverified until one physical PC test passes.
