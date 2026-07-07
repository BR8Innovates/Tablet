#!/usr/bin/env bash
# Copies the static PWA assets into www/ so Capacitor can bundle them into the native Android app.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf www
mkdir -p www
cp index.html app.js styles.css manifest.webmanifest service-worker.js www/
cp -r icons www/
