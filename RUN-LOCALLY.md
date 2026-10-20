# Run Fuel Station Manager on your own computer

1. Install **Node.js 22 or newer** (https://nodejs.org) — one-time.
2. Unzip this folder, then double-click **start.bat** (Windows) or run **./start.sh** (Mac/Linux).
3. Your browser opens http://localhost:3000. Click "New station? Create account".

Your accounts and data are saved in the `data` folder next to this file. **Back it up** (copy the folder) and never delete it.

**Phone/tablet on the same Wi-Fi:** find your computer's IP address (e.g. 192.168.1.20) and open `http://192.168.1.20:3000` on the phone. Staff can then log in with their own accounts from their own devices.
(Installing to the home screen needs HTTPS, so on a phone use it as a normal browser tab.)

No Node? start.bat / start.sh fall back to Python in "simple mode": the app works, but data stays in that one browser.
