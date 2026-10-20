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

## Run locally
```bash
cd fuelstation && python3 -m http.server 8080
```
(Needs `http://localhost` or HTTPS — password hashing uses Web Crypto.)

## Moving to a real SaaS
All reads/writes go through `js/store.js`, and every record is partitioned by station and has a UUID. Swap that module for API calls (and move `js/auth.js` + the role checks server-side) without touching the screens. Business rules for dashboards live in `js/calc.js` (`totals`, `litresByProduct`, `customerBalance`).

**Current limitation:** data and logins live in this browser's `localStorage`, so it is single-device and the client-side login is a convenience, not real security, until a backend exists.
