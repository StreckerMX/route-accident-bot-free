"""Estado de configuracion y persistencia."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

SETTINGS_FILE = "RouteAccidentBotFree.Settings.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "route": {
        "maps_link": "",
        "origin": "",
        "destination": "",
        "travel_mode": "DRIVE",
        "road_preference": "free",
    },
    "monitor": {
        "periodic_enabled": False,
        "interval_minutes": 45,
        "jam_delay_threshold_minutes": 13,
        "cooldown_minutes": 15,
    },
    "investigation": {
        "language": "es",
        "max_news_results": 5,
        "search_queries": [
            "accidente {road} {city}",
            "choque {road} {city} hoy",
            "trafico {road} {city}",
        ],
    },
    "advisor": {
        "alternative_routes": 2,
        "recommend_switch_if_saves_minutes": 10,
    },
    "telegram": {
        "enabled": False,
        "notify_on_alert": True,
        "notify_on_ok": False,
    },
}


def load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return _deep_copy(DEFAULT_CONFIG)
    with config_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return _merge_defaults(data)


def save_config(config_path: Path, config: dict[str, Any]) -> None:
    with config_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def write_env_file(
    env_path: Path,
    ors_key: str,
    tomtom_key: str,
    nominatim_email: str = "",
    telegram_token: str = "",
    telegram_chat_id: str = "",
) -> None:
    lines = [
        f"ORS_API_KEY={ors_key.strip()}",
        f"TOMTOM_API_KEY={tomtom_key.strip()}",
        f"NOMINATIM_EMAIL={nominatim_email.strip()}",
        "",
        f"TELEGRAM_BOT_TOKEN={telegram_token.strip()}",
        f"TELEGRAM_CHAT_ID={telegram_chat_id.strip()}",
    ]
    env_path.write_text("\n".join(lines), encoding="utf-8")


def is_config_complete(base_dir: Path) -> bool:
    env_path = base_dir / ".env"
    config_path = base_dir / SETTINGS_FILE
    if not env_path.exists() or not config_path.exists():
        return False

    load_dotenv(env_path, encoding="utf-8-sig")
    if not os.getenv("ORS_API_KEY", "").strip():
        return False
    if not os.getenv("TOMTOM_API_KEY", "").strip():
        return False

    config = load_config(config_path)
    route = config.get("route", {})
    if not route.get("origin", "").strip() or not route.get("destination", "").strip():
        return False
    if not route.get("maps_link", "").strip():
        return False
    return True


def _deep_copy(data: dict[str, Any]) -> dict[str, Any]:
    return yaml.safe_load(yaml.safe_dump(data)) or {}


def _merge_defaults(config: dict[str, Any]) -> dict[str, Any]:
    merged = _deep_copy(DEFAULT_CONFIG)
    for key, value in config.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    return merged