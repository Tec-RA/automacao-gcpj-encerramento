@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if not exist ".venv\Scripts\python.exe" (
  echo Ambiente virtual nao encontrado.
  echo Execute primeiro: powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m streamlit run streamlit_app.py
if errorlevel 1 pause
