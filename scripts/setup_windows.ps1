$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "=== Instalacao da Automacao GCPJ ===" -ForegroundColor Cyan

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    $created = $false
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($version in @("3.12", "3.11", "3.13")) {
            try {
                & py "-$version" -m venv .venv
                if ($LASTEXITCODE -eq 0) {
                    $created = $true
                    break
                }
            } catch {
                # Tenta a proxima versao.
            }
        }
    }

    if (-not $created) {
        if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
            throw "Python 3.11 ou superior nao encontrado. Instale o Python e execute novamente."
        }
        & python -m venv .venv
    }
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -c "import streamlit, playwright, pandas, openpyxl, yaml, filelock; print('Dependencias validadas.')"

Write-Host ""
Write-Host "Instalacao concluida." -ForegroundColor Green
Write-Host "Execute scripts\iniciar_app.bat para abrir a aplicacao."
