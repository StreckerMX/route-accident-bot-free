# Route Accident Bot FREE

[![Python](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![OpenRouteService](https://img.shields.io/badge/OpenRouteService-free-7CBD42)](https://openrouteservice.org/)
[![TomTom](https://img.shields.io/badge/TomTom-free%20tier-red)](https://developer.tomtom.com/)

Versión **100% gratuita** del monitor de rutas. No usa Google Maps API ni requiere tarjeta de crédito.

Analiza tu ruta, detecta incidentes de tráfico, busca noticias y recomienda si conviene cambiar de ruta.

[English](#english)

---

## APIs gratuitas que usa

| API | Para qué | Registro | Costo |
|-----|----------|----------|-------|
| [OpenRouteService](https://openrouteservice.org/dev/#/signup) | Calcular rutas y alternativas | Gratis, sin tarjeta | 2,000 req/día |
| [TomTom Traffic](https://developer.tomtom.com/user/register) | Detectar accidentes e incidentes | Gratis, sin tarjeta | 2,500 req/día |
| [Nominatim](https://nominatim.org/) | Ubicación (OpenStreetMap) | Solo correo | Gratis |
| DuckDuckGo | Noticias del incidente | No requiere | Gratis |

---

## Requisitos

- Windows con **Python 3.10+**
- API Key de **OpenRouteService** (gratis)
- API Key de **TomTom** (gratis)
- Correo para Nominatim (recomendado)
- *(Opcional)* Telegram

---

## Instalación (Windows)

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; irm https://raw.githubusercontent.com/StreckerMX/route-accident-bot-free/main/Install-Remote.ps1 | iex
```

Se instala en `%LOCALAPPDATA%\RouteAccidentBotFree` y abre la GUI de configuración (APIs, enlace de Maps, cuota/libre). Vuelve a ejecutar el comando para actualizar sin perder tu configuración.

---

## Uso

Acceso directo **Route Accident Bot FREE** o el mismo comando de instalación. Pulsa **Analizar ruta**; opcionalmente activa revisión automática cada 45 min.

---

## Desinstalación

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; irm https://raw.githubusercontent.com/StreckerMX/route-accident-bot-free/main/Uninstall-RouteAccidentBotFree.ps1 | iex
```

---

## Obtener las API Keys gratis

### OpenRouteService
1. Regístrate en https://openrouteservice.org/dev/#/signup
2. Crea un token en el panel
3. Pégalo como `ORS_API_KEY` en `.env`

### TomTom
1. Regístrate en https://developer.tomtom.com/user/register
2. Crea un proyecto y copia la API Key
3. Pégala como `TOMTOM_API_KEY` en `.env`

### Nominatim
- Solo agrega tu correo en `NOMINATIM_EMAIL` (política de uso de OpenStreetMap)

---

## Archivo `.env`

```env
ORS_API_KEY=tu_clave_ors
TOMTOM_API_KEY=tu_clave_tomtom
NOMINATIM_EMAIL=tu_correo@ejemplo.com

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

---

## Comparación con la versión Google

| | route-accident-bot | route-accident-bot-free |
|---|-------------------|------------------------|
| Costo | Requiere facturación Google | Gratis |
| Tarjeta de crédito | Sí (para prueba) | No |
| Tráfico en tiempo real | Muy preciso (Google) | TomTom + rutas ORS |
| Geocodificación | Google Geocoding | Nominatim (OSM) |

---

## Licencia

MIT

---

# English

Free route traffic monitor using OpenRouteService, TomTom Traffic, and Nominatim. No Google APIs, no credit card required.

## Install

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; irm https://raw.githubusercontent.com/StreckerMX/route-accident-bot-free/main/Install-Remote.ps1 | iex
```

## Run

Desktop shortcut or re-run install command. Click **Analizar ruta**.

## Free API signup

- OpenRouteService: https://openrouteservice.org/dev/#/signup
- TomTom: https://developer.tomtom.com/user/register

## License

MIT