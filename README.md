# GD OS

Gamers District Operating System. Local gaming-café software for station control, sessions, and billing.

Development happens on macOS. The café installation runs on Windows. Docker Compose is the server runtime in both places, so the API and PostgreSQL do not depend on macOS.

## What runs where

| Piece | Development (Mac) | Café (Windows) |
|---|---|---|
| API and PostgreSQL | Docker Desktop | Docker Desktop with WSL2, same `compose.yml` |
| Admin and cashier UI | Browser on the Mac | Browser on the cashier PC and admin PC |
| Gaming PC agent | Prints the server action. It does not cover this Mac. | `gdos-agent.exe` in the player session on each diskless PC |
| CCBoot | Not involved | PXE boot, images, write-back. GD OS does not replace it |

## Current status

Working now:

- `GET /health` and `GET /ready`
- PostgreSQL catalog for stations, hourly rates, and packages
- Seed data for the 15 PCs, 3 PS5s, 2 simulators, and the cashier workstation
- Prices stored in rupees (`150.00`) and read back from the database
- Staff login with Argon2id passwords, roles, and an audit log
- Customer registration and username login, plus cashier walk-in registration
- Session start, extension, and end, with rupee charges calculated on the server
- Cashier screen for the floor, session start, extension, and payment at the end
- PC pairing and a heartbeat that returns lock or unlock from the server
- Daily takings in rupees, using the Asia/Kolkata day, on the cashier floor
- Database backup and a confirmed restore that leaves the Docker volume in place
- Station reservations that cannot overlap, shown on the cashier floor
- A receipt for each closed session, shown after payment
- Maintenance and disabled stations, which stay out of play until a manager returns them
- A Windows PC agent that covers the desktop when the server says lock, and hides that cover when a session is active
- Peak and off-peak hourly rates for new sessions, in Asia/Kolkata time
- Station use for the Asia/Kolkata day, separate from the amount billed

The Windows cover has not been tried on a diskless PC. The Mac build only prints `LOCK` or `UNLOCK`.

## Run the health check on this Mac

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

To start the containers:

```bash
cp .env.example .env
docker compose up -d --build
curl http://localhost:8000/health
```

The cashier screen is `http://localhost:8000` after the containers are up. Sign in with the staff username from `.env`.

Windows production steps are in [DEPLOYMENT.md](DEPLOYMENT.md).

## Layout

```
backend/     FastAPI service
frontend/    Cashier screen
agent/       PC heartbeat. Mac simulator, and the Windows agent project
compose.yml  API + PostgreSQL
```

Documentation: [ARCHITECTURE.md](ARCHITECTURE.md), [DATABASE.md](DATABASE.md), [API_DOCUMENTATION.md](API_DOCUMENTATION.md), [TESTING.md](TESTING.md), [DEPLOYMENT.md](DEPLOYMENT.md), [SECURITY.md](SECURITY.md), [CHANGELOG.md](CHANGELOG.md).
