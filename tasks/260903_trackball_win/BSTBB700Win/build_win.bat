@echo off
REM Win11 build: single exe via PyInstaller
python --version
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name BSTBB700Win app.py
echo done: dist\BSTBB700Win.exe
