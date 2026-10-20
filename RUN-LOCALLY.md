# Run Fuel Station Manager on your own computer

1. Install **Node.js 22 or newer** (https://nodejs.org) — one-time.
2. Unzip this folder, then double-click **start.bat** (Windows) or run **./start.sh** (Mac/Linux).
3. Your browser opens http://localhost:3000. Click "New station? Create account".

Your accounts and data are saved in the `data` folder next to this file. **Back it up** (copy the folder) and never delete it.

**Phone/tablet on the same Wi-Fi:** find your computer's IP address (e.g. 192.168.1.20) and open `http://192.168.1.20:3000` on the phone. Staff can then log in with their own accounts from their own devices.
(Installing to the home screen needs HTTPS, so on a phone use it as a normal browser tab.)

No Node? start.bat / start.sh fall back to Python in "simple mode": the app works, but data stays in that one browser.

## Backups
A copy of your data is saved automatically every day in `data/backups` (the last 14 are kept). To restore, stop the app and copy a backup over `data/fuelstation.db`. Keep another copy on a USB drive or cloud folder too.

## Forgot a password?
Staff passwords can be reset by the owner (Setup → Team). If the owner forgets theirs, run in this folder:

    npm run reset-password -- <username> <new-password>
