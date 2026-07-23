@echo off
setlocal
set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "PROFILE=C:\chrome_gcpj_debug"

if not exist "%CHROME%" (
  echo Google Chrome nao encontrado em: %CHROME%
  pause
  exit /b 1
)

start "Chrome GCPJ" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%PROFILE%" --start-maximized --no-first-run --no-default-browser-check
