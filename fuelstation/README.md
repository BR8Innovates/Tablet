# Fuel Station Manager

Mobile-first PWA for running a fuel station day to day. Lives in `fuelstation/` (the Vitals app in the repo root is unrelated).

## What it does
- **Login & roles** — each station is its own tenant. Roles: *owner* (everything + team), *manager* (everything else), *attendant* (daily entry + customers only).
- **Setup** — products, pumps/nozzles, **daily price** per product (effective-dated), **shifts** (set the count and timings), expense types, online payment sources, team, JSON backup.
- **Daily tracking** — pick date + shift; enter opening/closing meter per pump (opening pre-fills from the previous closing) → litres × that day's price = sales.
- **Daily payments** — online collections by source, credit sales and payments received per customer, expenses by type (paid, or on credit and marked paid later).
- **Unified customer module** — one balance per customer (credit − payments), full statement, credit limit warning.
- **Payment records** — every receipt and expense, filterable by range, cash vs online and online source, with totals per source.
- **Cash reconciliation** — expected cash = fuel sales − online − credit + customer cash − cash expenses; compare with cash counted.

## Run it
**With the backend (real accounts, multi-device sync):**
```bash
npm start            # Node >= 22.5, no dependencies → http://localhost:3000
```
`server/index.js` serves the app and the API, and keeps everything in a SQLite file under `data/` (override with `DATA_DIR`; set `SESSION_SECRET` in production, and put it behind HTTPS). Or use the `Dockerfile` with a volume on `/data`.

- Each station is a separate tenant; passwords are scrypt-hashed; sessions are signed tokens (30 days).
- Roles are enforced **on the server**: attendants can only write daily entries (readings, credit, payments, expenses, closing) and customers; only the owner manages the team.
- The app keeps a copy of your station's data on the device, so screens are instant and entries made offline are queued and sent when the connection returns (top bar shows "Offline · n waiting"). It refreshes from the server when you return to the app.
- Conflicts are last-write-wins per record.

**Without a backend** (e.g. GitHub Pages): the app detects there is no server and runs in local mode — data and logins stay in this browser only.

## Project layout
`js/store.js` data layer (remote + local), `js/auth.js` sign-in, `js/calc.js` business rules and analytics, `js/views/*` screens, `../server/index.js` API.

**Still to do for production:** HTTPS/hosting, password reset, backups of `data/fuelstation.db`, and a Postgres move if you outgrow one SQLite file.
