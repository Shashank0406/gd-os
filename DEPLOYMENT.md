# Deployment

## Target

The café server is a Windows PC on the local network. Docker Desktop (WSL2 backend) runs the same `compose.yml` used on the development Mac. The API container and PostgreSQL container are Linux images. Windows is the host, not the language runtime.

Gaming PCs do not run this Compose stack. They boot through CCBoot and, later, run the GD OS Windows agent.

The cashier PC only needs a browser pointed at `http://<server-lan-ip>:8000`. Public internet is not required for that.

## Develop on the Mac

```bash
cp .env.example .env
docker compose up -d --build
curl http://localhost:8000/health
```

Edit `.env` before any real data is stored. `POSTGRES_PASSWORD` and `DATABASE_URL` must match.

## Install on the Windows server

1. Install Docker Desktop for Windows and enable WSL2. Set it to start when Windows signs in.
2. Copy this repository to the server, or clone it. Do not copy a Mac `.venv` or `node_modules`.
3. Copy `.env.example` to `.env` and replace `change-me` with a long password.
4. In PowerShell, from the repository folder:

```powershell
docker compose up -d --build
curl http://localhost:8000/health
```

5. Allow inbound TCP 8000 from the café LAN only. Keep PostgreSQL port 5432 off the public firewall. Other café PCs should reach the database only if an admin tool needs it; the API container already can.
6. Confirm a reboot brings the containers back (`restart: unless-stopped` plus Docker starting with Windows). This reboot test has not been done yet.

Relative compose paths are valid on both operating systems. Do not introduce `/Users/...` paths into Compose, scripts, or settings.

## Data

PostgreSQL data lives in the Docker volume `gd_os_pgdata`. Removing the container does not remove that volume. `docker compose down -v` does delete it. Do not use `-v` on the café server.

Backups are not scripted yet. Until they exist, this stack is not ready for live takings.

## Windows agent build, later

The heartbeat protocol and Mac simulator exist. The Windows service is still unpublished. It will be published from the Mac for a 64-bit Windows PC:

```bash
dotnet publish -c Release -r win-x64 --self-contained
```

That step needs the .NET 8 SDK. This Mac currently has .NET SDK 7, which is out of support. The agent project is not created yet, and lock/unlock is not claimed to work.

## Not verified from this Mac

- Docker Desktop auto-start after a Windows reboot
- Windows firewall rules
- A diskless PC talking to the server
- CCBoot image behaviour with an agent installed
