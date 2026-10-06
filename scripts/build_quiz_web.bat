@echo off
rem ============================================================
rem  build_quiz_web.bat - build dist\quiz_web.exe via PyInstaller
rem  Run from anywhere. Output goes to dist\ (git-ignored; not committed).
rem  Requires: py -3 -m pip install pyinstaller  (or python -m pip ...)
rem ============================================================
setlocal
cd /d "%~dp0.."

set "PYCMD="
py -3 -c "import sys" >nul 2>nul
if not errorlevel 1 set "PYCMD=py -3"
if not defined PYCMD (
  python -c "import sys" >nul 2>nul
  if not errorlevel 1 set "PYCMD=python"
)
if not defined PYCMD (
  echo [ERROR] Python 3 was not found.
  echo Install Python 3 from https://www.python.org/ and add it to PATH.
  pause
  exit /b 1
)

%PYCMD% -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] PyInstaller was not found.
  echo Install it with:  %PYCMD% -m pip install pyinstaller
  pause
  exit /b 1
)

echo Building dist\quiz_web.exe ...
%PYCMD% -m PyInstaller --noconfirm --onefile --name quiz_web ^
  --paths scripts ^
  --add-data "scripts/quiz_webui;quiz_webui" ^
  scripts\quiz_web.py
set "EC=%ERRORLEVEL%"

if not "%EC%"=="0" (
  echo [ERROR] Build failed with code %EC%.
  pause
  exit /b %EC%
)

echo Build complete: dist\quiz_web.exe
echo Note: dist\ build\ and *.spec are git-ignored (do not commit them).
exit /b 0
