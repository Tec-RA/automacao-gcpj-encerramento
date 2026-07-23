$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "=== Diagnostico GCPJ ==="
Write-Host ""
Write-Host "Python:"
if (Test-Path .\.venv\Scripts\python.exe) {
    & .\.venv\Scripts\python.exe --version
} else {
    Write-Warning "Ambiente .venv nao encontrado."
}

Write-Host ""
Write-Host "Chrome:"
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (Test-Path $chrome) {
    Write-Host $chrome
} else {
    Write-Warning "Chrome nao encontrado no caminho padrao."
}

Write-Host ""
Write-Host "Porta 9222:"
Test-NetConnection -ComputerName 127.0.0.1 -Port 9222 | Select-Object ComputerName, RemotePort, TcpTestSucceeded

Write-Host ""
Write-Host "Endpoint CDP:"
try {
    Invoke-RestMethod http://127.0.0.1:9222/json/version | ConvertTo-Json -Depth 4
} catch {
    Write-Warning $_.Exception.Message
}
