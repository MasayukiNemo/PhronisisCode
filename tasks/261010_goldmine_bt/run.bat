@echo off
chcp 65001 >nul
cd /d %~dp0
echo === goldmine-bt ===
echo 1: selftest
echo 2: fetch (Yahoo)
echo 3: run EURUSD
echo 4: walk-forward EURUSD
set /p M="select [1-4]: "
if "%M%"=="1" python -m bt.run --selftest
if "%M%"=="2" python data/fetch.py
if "%M%"=="3" python -m bt.run --csv data/EURUSD=X.csv --symbol EURUSD --out equity_curve.csv --db trades.db
if "%M%"=="4" python walk_forward.py --csv data/EURUSD=X.csv --symbol EURUSD --out os_results.csv
pause
