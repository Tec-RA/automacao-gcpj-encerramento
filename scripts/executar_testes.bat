@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONUTF8=1"

if not exist ".venv\Scripts\python.exe" (
  echo Ambiente virtual nao encontrado.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
".venv\Scripts\python.exe" -m ruff check .
if errorlevel 1 goto :erro
".venv\Scripts\python.exe" -m pytest
if errorlevel 1 goto :erro

echo Testes concluidos com sucesso.
pause
exit /b 0

:erro
echo A validacao encontrou erros.
pause
exit /b 1
