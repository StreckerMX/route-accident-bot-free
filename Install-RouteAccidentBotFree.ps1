#Requires -Version 5.1

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot "venv"
$EnvFile = Join-Path $ProjectRoot ".env"
$ConfigFile = Join-Path $ProjectRoot "RouteAccidentBotFree.Settings.yaml"
$RequirementsFile = Join-Path $ProjectRoot "RouteAccidentBotFree.Requirements.txt"
$EntryPoint = Join-Path $ProjectRoot "Start-RouteAccidentBotFree.py"

function Write-Step([string]$Text) { Write-Host "`n$Text" -ForegroundColor Cyan }
function Write-Ok([string]$Text) { Write-Host "  Listo: $Text" -ForegroundColor Green }
function Write-Err([string]$Text) { Write-Host "  Error: $Text" -ForegroundColor Red }

function Read-InputDefault {
    param([string]$Prompt, [string]$Default = "")
    if ($Default) {
        $raw = Read-Host "$Prompt [$Default]"
        if ([string]::IsNullOrWhiteSpace($raw)) { return $Default }
        return $raw.Trim()
    }
    return (Read-Host $Prompt).Trim()
}

function Read-Secret {
    param([string]$Prompt)
    $secure = Read-Host $Prompt -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

function Read-YesNo {
    param([string]$Prompt, [bool]$DefaultYes = $false)
    $hint = if ($DefaultYes) { "S/n" } else { "s/N" }
    $answer = (Read-Host "$Prompt ($hint)").Trim().ToLower()
    if ([string]::IsNullOrWhiteSpace($answer)) { return $DefaultYes }
    return $answer -in @("s", "si", "sí", "y", "yes")
}

function Set-YamlValue {
    param([string]$FilePath, [string]$KeyPath, [string]$Value, [bool]$Quoted = $true)
    $content = Get-Content $FilePath -Raw -Encoding UTF8
    $formatted = if ($Quoted) { "`"$Value`"" } else { $Value }
    $pattern = "(?m)^(\s*$([regex]::Escape($KeyPath)):\s*).*$"
    if ($content -match $pattern) {
        $content = [regex]::Replace($content, $pattern, "`${1}$formatted")
    }
    Set-Content $FilePath $content -Encoding UTF8 -NoNewline
}

function Write-TextFileUtf8NoBom {
    param([string]$Path, [string]$Content)
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Test-Telegram {
    param([string]$Token, [string]$ChatId)
    $url = "https://api.telegram.org/bot$Token/sendMessage"
    $body = @{ chat_id = $ChatId; text = "Route Accident Bot FREE: configuracion correcta." } | ConvertTo-Json
    $r = Invoke-RestMethod -Uri $url -Method Post -Body $body -ContentType "application/json"
    return $r.ok -eq $true
}

Clear-Host
Write-Host "`n  Route Accident Bot FREE - Instalacion`n" -ForegroundColor Cyan
Set-Location $ProjectRoot

Write-Step "1/5  Verificando Python..."
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)" -and ([int]$Matches[1] -gt 3 -or ([int]$Matches[1] -eq 3 -and [int]$Matches[2] -ge 10))) {
            $pythonCmd = $cmd
            break
        }
    } catch {}
}
if (-not $pythonCmd) { Write-Err "Se requiere Python 3.10+."; exit 1 }
Write-Ok "Python detectado"

Write-Step "2/5  Preparando entorno..."
if (-not (Test-Path (Join-Path $VenvPath "Scripts\python.exe"))) {
    & $pythonCmd -m venv $VenvPath
}
$venvPython = Join-Path $VenvPath "Scripts\python.exe"
Write-Ok "Entorno listo"

Write-Step "3/5  Instalando dependencias..."
& $venvPython -m pip install --upgrade pip -q
& $venvPython -m pip install -r $RequirementsFile -q
Write-Ok "Dependencias instaladas"

Write-Step "4/5  Configuracion"
$reconfigure = $true
if ((Test-Path $EnvFile) -and -not (Read-YesNo "  Ya existe .env. Reconfigurar" $false)) {
    $reconfigure = $false
}

$orsKey = ""
$tomtomKey = ""
$nominatimEmail = ""
$enableTelegram = $false
$telegramToken = ""
$telegramChatId = ""

if ($reconfigure) {
    Write-Host ""
    Write-Host "  APIs 100% gratuitas (sin tarjeta de credito):" -ForegroundColor DarkGray
    Write-Host "  - OpenRouteService: https://openrouteservice.org/dev/#/signup" -ForegroundColor DarkGray
    Write-Host "  - TomTom: https://developer.tomtom.com/user/register`n" -ForegroundColor DarkGray

    $orsKey = Read-Secret "  API Key - OpenRouteService"
    while ([string]::IsNullOrWhiteSpace($orsKey)) { $orsKey = Read-Secret "  API Key - OpenRouteService" }

    $tomtomKey = Read-Secret "  API Key - TomTom"
    while ([string]::IsNullOrWhiteSpace($tomtomKey)) { $tomtomKey = Read-Secret "  API Key - TomTom" }

    $nominatimEmail = Read-InputDefault "  Correo para Nominatim (OpenStreetMap)" ""

    $enableTelegram = Read-YesNo "  Activar Telegram" $false
    if ($enableTelegram) {
        $telegramToken = Read-Secret "  Token de Telegram"
        $telegramChatId = Read-InputDefault "  Chat ID de Telegram" ""
    }
}

$origin = Read-InputDefault "  Origen" "Ciudad de Mexico, CDMX"
$destination = Read-InputDefault "  Destino" "Toluca, Estado de Mexico"

Write-Step "5/5  Guardando configuracion..."
if ($reconfigure) {
    $envLines = @(
        "ORS_API_KEY=$orsKey"
        "TOMTOM_API_KEY=$tomtomKey"
        "NOMINATIM_EMAIL=$nominatimEmail"
        ""
        "TELEGRAM_BOT_TOKEN=$telegramToken"
        "TELEGRAM_CHAT_ID=$telegramChatId"
    )
    Write-TextFileUtf8NoBom -Path $EnvFile -Content ($envLines -join "`n")
    Write-Ok "Archivo .env"
}

Set-YamlValue $ConfigFile "  origin" $origin
Set-YamlValue $ConfigFile "  destination" $destination
Set-YamlValue $ConfigFile "  interval_minutes" "45" -Quoted $false
Set-YamlValue $ConfigFile "  jam_delay_threshold_minutes" "13" -Quoted $false

if ($reconfigure) {
    $content = Get-Content $ConfigFile -Raw -Encoding UTF8
    $flag = if ($enableTelegram) { "true" } else { "false" }
    $content = $content -replace '(?m)^(\s*enabled:\s*).*$', "`${1}$flag"
    Set-Content $ConfigFile $content -Encoding UTF8 -NoNewline
}
Write-Ok "RouteAccidentBotFree.Settings.yaml"

if ($reconfigure -and $enableTelegram) {
    try {
        if (Test-Telegram $telegramToken $telegramChatId) { Write-Ok "Telegram verificado" }
    } catch {}
}

Write-Host "`n  Instalacion completada.`n" -ForegroundColor Green
Write-Host "  Iniciar el bot:" -ForegroundColor Cyan
Write-Host "    .\Start-RouteAccidentBotFree.ps1" -ForegroundColor Yellow
Write-Host "    .\Uninstall-RouteAccidentBotFree.ps1  (eliminar todo)`n" -ForegroundColor DarkGray

if (Read-YesNo "  Iniciar ahora" $false) {
    & $venvPython $EntryPoint
}