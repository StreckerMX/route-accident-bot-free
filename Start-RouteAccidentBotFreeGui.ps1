#Requires -Version 5.1
<#
.SYNOPSIS
    Inicia la interfaz grafica de Route Accident Bot FREE.
.EXAMPLE
    .\Start-RouteAccidentBotFreeGui.ps1
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$EntryPoint = Join-Path $ProjectRoot "Start-RouteAccidentBotFreeGui.py"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Error: no se encontro el entorno virtual." -ForegroundColor Red
    Write-Host "Ejecuta primero: .\Install-RouteAccidentBotFree.ps1" -ForegroundColor Yellow
    exit 1
}

& $VenvPython $EntryPoint