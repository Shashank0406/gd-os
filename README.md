# GD OS

Gamers District Operating System. Local gaming-café software for station control, sessions, and billing.

Development happens on macOS. The café installation runs on Windows. Docker Compose is the server runtime in both places, so the API and PostgreSQL do not depend on macOS.

## What runs where

| Piece | Development (Mac) | Café (Windows) |
|---|---|---|
| API and PostgreSQL | Docker Desktop | Docker Desktop with WSL2, same `compose.yml` |
| Admin and cashier UI | Browser on the Mac | Browser on the cashier PC and admin PC |
| Gaming PC agent | Simulator on the Mac, later | Native Windows service on each diskless PC |
| CCBoot | Not involved | PXE boot, images, write-back. GD OS does not replace it |

## Day 1 status

Working now:

- Repository layout
- `GET /health` on the API
- PostgreSQL 16 service definition with a named volume
- One automated health test

Not built yet: database schema, login, pricing, sessions, cashier UI, Windows agent.

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

Windows production steps are in [DEPLOYMENT.md](DEPLOYMENT.md).

## Layout

```
backend/     FastAPI service
frontend/    React app (not started)
agent/       Windows agent (not started)
compose.yml  API + PostgreSQL
```

Documentation: [ARCHITECTURE.md](ARCHITECTURE.md), [DATABASE.md](DATABASE.md), [API_DOCUMENTATION.md](API_DOCUMENTATION.md), [TESTING.md](TESTING.md), [DEPLOYMENT.md](DEPLOYMENT.md), [SECURITY.md](SECURITY.md), [CHANGELOG.md](CHANGELOG.md).
