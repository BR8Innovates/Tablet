#!/usr/bin/env bash
# Regenerates the Capacitor-scaffolded placeholder launcher icons from the app's
# real icons (icons/icon-512.png, icons/icon-maskable-512.png) using ImageMagick.
set -euo pipefail
cd "$(dirname "$0")/.."

RES=android/app/src/main/res
LEGACY_SRC=icons/icon-512.png
ADAPTIVE_SRC=icons/icon-maskable-512.png

declare -A LEGACY_SIZES=( [mdpi]=48 [hdpi]=72 [xhdpi]=96 [xxhdpi]=144 [xxxhdpi]=192 )
declare -A FOREGROUND_SIZES=( [mdpi]=108 [hdpi]=162 [xhdpi]=216 [xxhdpi]=324 [xxxhdpi]=432 )

for density in "${!LEGACY_SIZES[@]}"; do
  size=${LEGACY_SIZES[$density]}
  convert "$LEGACY_SRC" -resize "${size}x${size}" "$RES/mipmap-$density/ic_launcher.png"
  convert "$LEGACY_SRC" -resize "${size}x${size}" "$RES/mipmap-$density/ic_launcher_round.png"
done

for density in "${!FOREGROUND_SIZES[@]}"; do
  size=${FOREGROUND_SIZES[$density]}
  convert "$ADAPTIVE_SRC" -resize "${size}x${size}" "$RES/mipmap-$density/ic_launcher_foreground.png"
done

# Match the adaptive icon background to the app's theme color (see manifest.webmanifest).
sed -i 's/#FFFFFF/#0f172a/' "$RES/values/ic_launcher_background.xml"

echo "Android launcher icons regenerated from $LEGACY_SRC / $ADAPTIVE_SRC"
