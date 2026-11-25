@echo off
cd /d "%~dp0"
if not exist .venv (
  py -3.12 -m venv .venv
  if errorlevel 1 python -m venv .venv
)
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run.py
pause
