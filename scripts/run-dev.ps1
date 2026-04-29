param(
    [int]$Port = $(if ($env:APP_PORT) { [int]$env:APP_PORT } else { 18088 })
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port $Port --env-file .env
