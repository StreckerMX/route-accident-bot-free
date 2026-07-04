#!/usr/bin/env python3
"""Monitor de tráfico gratuito — sin APIs de pago de Google."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

from route_accident_bot_free.monitor_service import RouteMonitor, load_config

SETTINGS_FILE = "RouteAccidentBotFree.Settings.yaml"


def main() -> int:
    base_dir = Path(__file__).parent
    load_dotenv(base_dir / ".env", encoding="utf-8-sig")

    config_path = base_dir / SETTINGS_FILE
    if not config_path.exists():
        print(f"Error: no se encontró {config_path}")
        return 1

    try:
        monitor = RouteMonitor(base_dir=base_dir, config=load_config(config_path))
    except ValueError as exc:
        print(f"Error: {exc}")
        if "ORS_API_KEY" in str(exc):
            print("Registro gratuito: https://openrouteservice.org/dev/#/signup")
        if "TOMTOM_API_KEY" in str(exc):
            print("Registro gratuito: https://developer.tomtom.com/user/register")
        return 1

    monitor.run_blocking()
    return 0


if __name__ == "__main__":
    sys.exit(main())