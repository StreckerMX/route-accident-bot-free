#Requires -Version 5.1

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$EntryPoint = Join-Path $ProjectRoot "Start-RouteAccidentBotFree.py"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Error: ejecuta primero .\Install-RouteAccidentBotFree.ps1" -ForegroundColor Red
    exit 1
}

& $VenvPython $EntryPoint