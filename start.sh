#!/bin/sh
# Fuel Station Manager — local launcher (Mac / Linux). Opens http://localhost:3000
cd "$(dirname "$0")"
if command -v node >/dev/null 2>&1 && node -e 'process.exit(+process.versions.node.split(".")[0]>=22?0:1)'; then
  echo "Starting with Node (accounts + data saved in ./data)…"
  (sleep 1; (open http://localhost:3000 || xdg-open http://localhost:3000) >/dev/null 2>&1) &
  exec node --no-warnings server/index.js
elif command -v python3 >/dev/null 2>&1; then
  echo "Node 22+ not found — starting simple mode with Python (data stays in this browser)."
  (sleep 1; (open http://localhost:3000 || xdg-open http://localhost:3000) >/dev/null 2>&1) &
  cd fuelstation && exec python3 -m http.server 3000
else
  echo "Please install Node.js 22 or newer from https://nodejs.org"; exit 1
fi
