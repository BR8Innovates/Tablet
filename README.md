# Vitals — Health & Activity Tracker

A installable, offline-first Progressive Web App (PWA) for tracking daily health and activity: steps, water intake, active minutes, sleep, and body measurements (weight, body fat, resting heart rate).

All data is stored **only on your device** (browser `localStorage`) — nothing is sent to a server. An on-demand **Insights** panel analyzes your logged data (weekly trends, streaks, best days, sleep-vs-activity patterns) whenever you tap "Generate insights."

## Features

- **Dashboard** — daily progress rings for steps, water, active minutes, and sleep; weekly step chart; weight trend; goal streaks; on-demand insights
- **Activity** — log workouts (walk, run, cycle, strength, yoga, sport), auto-estimated calories, weekly/30-day charts
- **Water** — quick-add buttons, big progress ring, 7-day history
- **Sleep** — log bedtime/wake time and quality, 7-day chart
- **Body** — log weight, body fat %, resting heart rate, 30-day trend
- **Settings** — customize daily goals, profile, export/import your data as JSON, reset

## Installing on a tablet

Once deployed (see below), open the site's URL in your tablet's browser:

**iPad (Safari):**
1. Open the URL in Safari
2. Tap the **Share** icon
3. Tap **Add to Home Screen**
4. Launch "Vitals" from your home screen — it opens full-screen, like a native app

**Android tablet (Chrome):**
1. Open the URL in Chrome
2. Tap the **⋮** menu
3. Tap **Install app** (or **Add to Home screen**)
4. Launch "Vitals" from your home screen or app drawer

Once installed, the app works fully **offline** — a service worker caches the app shell on first load.

## Deployment

This repo includes a GitHub Actions workflow (`.github/workflows/deploy-pages.yml`) that publishes the static site to **GitHub Pages** on every push. Enable Pages once under repo **Settings → Pages → Source: GitHub Actions**, then the deployed URL will be shown in the workflow run summary (and under Settings → Pages).

## Installing as a native Android APK (sideload)

For a real, installable APK instead of a browser-based PWA install, this repo wraps the same app in a [Capacitor](https://capacitorjs.com/) Android shell (see `android/`). The APK bundles the web assets directly, so it works fully offline with no server or browser involved. It's a debug-signed build meant for installing on your own device only — it is not published to the Play Store.

**Get the APK:**
- Go to the repo's **Releases** page and download `app-debug.apk` from the `android-latest` release (updated automatically on every push), **or**
- Go to **Actions → Build Android APK → (latest run)** and download the `vitals-debug-apk` artifact.

**Install on your Android device:**
1. Transfer `app-debug.apk` to your device (download link, USB, etc.).
2. Open the file. Android will prompt to allow installs from that source — tap **Settings** and enable **Install unknown apps** for the app you used to open it (browser or file manager).
3. Tap **Install**, then launch **Vitals** from your app drawer.

Note: the native app's data storage is separate from any browser-based PWA install of the same site. If you already have data in the browser version, use **Settings → Export data** there and **Settings → Import data** in the app to bring it across.

**Building it yourself:** with Node.js and a JDK installed, run `npm install`, then `./scripts/prepare-www.sh && npx cap sync android && cd android && ./gradlew assembleDebug`. The APK lands at `android/app/build/outputs/apk/debug/app-debug.apk`.

## Local development

No build step required — it's plain HTML/CSS/JS. To preview locally:

```bash
python3 -m http.server 8080
```

Then open `http://localhost:8080`. (Service workers require `http://localhost` or `https://` — opening `index.html` directly via `file://` will work for the UI but the service worker and installability features need a served origin.)

## Data & privacy

- All entries live in your browser's `localStorage` under the key `vitals:v1`.
- Use **Settings → Export data** to download a JSON backup, and **Import data** to restore it (e.g. after clearing browser data or moving to a new device).
- **Reset all data** permanently deletes everything on that device.
