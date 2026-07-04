#Requires -Version 5.1
<#
.SYNOPSIS
    Elimina Route Accident Bot FREE y todos sus archivos.
#>

$ErrorActionPreference = "Stop"
$ConfirmWord = "BORRAR"
$LocalAppDir = Join-Path $env:LOCALAPPDATA "RouteAccidentBotFree"

function Read-YesNo {
    param([string]$Prompt, [bool]$DefaultYes = $false)
    $hint = if ($DefaultYes) { "S/n" } else { "s/N" }
    $answer = (Read-Host "$Prompt ($hint)").Trim().ToLower()
    if ([string]::IsNullOrWhiteSpace($answer)) { return $DefaultYes }
    return $answer -in @("s", "si", "sí", "y", "yes")
}

function Remove-ProjectDir([string]$ProjectRoot) {
    if (-not (Test-Path $ProjectRoot)) { return $true }
    try {
        Remove-Item -LiteralPath $ProjectRoot -Recurse -Force
        return $true
    } catch {
        Write-Host "  No se pudo eliminar $ProjectRoot" -ForegroundColor Yellow
        return $false
    }
}

Clear-Host
Write-Host "`n  Route Accident Bot FREE - Desinstalacion`n" -ForegroundColor Red

$targets = @()
if (Test-Path $LocalAppDir) { $targets += $LocalAppDir }
if ((Test-Path $PSScriptRoot) -and ($PSScriptRoot -notin $targets)) { $targets += $PSScriptRoot }

if ($targets.Count -eq 0) {
    Write-Host "  No se encontro ninguna instalacion.`n" -ForegroundColor Yellow
    exit 0
}

Write-Host "  Se eliminara:" -ForegroundColor Yellow
$targets | ForEach-Object { Write-Host "    $_" -ForegroundColor White }

if (-not (Read-YesNo "  Continuar" $false)) { exit 0 }
if ((Read-Host "  Escribe $ConfirmWord para confirmar").Trim() -ne $ConfirmWord) { exit 0 }

foreach ($dir in $targets) {
    Write-Host "`n  Eliminando $dir ..." -ForegroundColor Cyan
    Remove-ProjectDir $dir | Out-Null
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcut = Join-Path $desktop "Route Accident Bot FREE.lnk"
if (Test-Path $shortcut) { Remove-Item $shortcut -Force }

Write-Host "`n  Desinstalacion completada.`n" -ForegroundColor Green