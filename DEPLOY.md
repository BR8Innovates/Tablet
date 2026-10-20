# Hosting Fuel Station Manager online

The app is one small Node server (API + live sync + the web app) with a SQLite file for data.
Host it anywhere that runs Docker or Node 22+ **and keeps a persistent disk**. Live sync keeps one connection open per device, so choose a host that stays running (no scale-to-zero) and run a **single instance**.

## Option A — Render (simplest, all clicks)
1. Push this repo to GitHub (or GitLab).
2. Render dashboard → **New → Blueprint** → select the repo. It reads `render.yaml`.
3. Deploy. Render gives you an `https://….onrender.com` address; add your own domain under Settings → Custom Domains.

## Option B — Fly.io (cheap, command line)
```bash
fly launch --no-deploy --copy-config      # edit app name in fly.toml first
fly volumes create fuel_data --size 1 --region bom
fly secrets set SESSION_SECRET=$(openssl rand -hex 32)
fly deploy
```

## Option C — your own server / VPS
```bash
docker build -t fuelstation .
docker run -d --restart=always -p 3000:3000 -v /srv/fuel-data:/data \
  -e TRUST_PROXY=1 -e SESSION_SECRET=$(openssl rand -hex 32) fuelstation
```
Put it behind HTTPS (e.g. Caddy: `yourdomain.com { reverse_proxy localhost:3000 }`).

## Settings (environment variables)
| Variable | Meaning |
|---|---|
| `SESSION_SECRET` | Long random string that signs logins. **Set it** and keep it the same between restarts. |
| `DATA_DIR` | Where the database and backups live — must be on the persistent disk (`/data` in Docker). |
| `TRUST_PROXY=1` | Set when behind a host/proxy so login limits use the real visitor address and HSTS is sent. |
| `PORT` | Defaults to 3000. |

## After it is live
- Open the address, **Create account** (this becomes your owner login), then add staff under Setup → Team. Each staff member signs in on their own phone and all screens update live.
- **HTTPS is required** for "Add to Home Screen" install and for secure logins.
- Daily backups are written to `DATA_DIR/backups` (last 14). Also copy them off the server now and then.
- Forgot the owner password: run `npm run reset-password -- <username> <new-password>` on the server (`fly ssh console` / Render Shell).
- Updating: push new code; the host rebuilds. Your data stays on the disk.
- Growing beyond one server or one SQLite file means moving the database to Postgres — plan for that when you have many stations.
