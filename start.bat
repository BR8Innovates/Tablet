@echo off
REM Fuel Station Manager - local launcher (Windows). Opens http://localhost:3000
cd /d "%~dp0"
where node >nul 2>nul
if %errorlevel%==0 (
  for /f %%v in ('node -p "process.versions.node.split('.')[0]"') do set NODEV=%%v
)
if defined NODEV if %NODEV% GEQ 22 (
  echo Starting with Node - accounts and data are saved in the data folder.
  start "" http://localhost:3000
  node --no-warnings server\index.js
  goto :eof
)
where python >nul 2>nul
if %errorlevel%==0 (
  echo Node 22+ not found - starting simple mode with Python. Data stays in this browser.
  start "" http://localhost:3000
  cd fuelstation
  python -m http.server 3000
  goto :eof
)
echo Please install Node.js 22 or newer from https://nodejs.org
pause
