@echo off
rem ============================================================
rem  quiz_web.bat - Gemini Quiz (Rich Web UI) launcher for Windows
rem  Runs: python scripts\quiz_web.py  (see scripts\quiz_webui\)
rem  Usage guide: docs\quiz_web\README.md
rem  Tip: "quiz_web.bat --stub" runs an offline demo (no quota).
rem ============================================================
setlocal
cd /d "%~dp0"
title Gemini Quiz (Rich Web UI)

set "PYCMD="
py -3 -c "import sys" >nul 2>nul
if not errorlevel 1 set "PYCMD=py -3"
if not defined PYCMD (
  python -c "import sys" >nul 2>nul
  if not errorlevel 1 set "PYCMD=python"
)
if not defined PYCMD (
  echo.
  echo [ERROR] Python 3 was not found.
  echo Install Python 3 from https://www.python.org/ and add it to PATH.
  echo Avoid the Microsoft Store placeholder; install the real Python.
  echo.
  pause
  exit /b 1
)

echo Starting Gemini Quiz (Rich Web UI)...
echo Usage guide: docs\quiz_web\README.md
echo The browser opens automatically. Do NOT close this window unless you want to stop the server.
echo.
%PYCMD% "scripts\quiz_web.py" %*
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo.
  echo [ERROR] Exited with code %EC%.
  pause
)
exit /b %EC%
