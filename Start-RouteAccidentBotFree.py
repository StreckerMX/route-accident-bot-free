#!/usr/bin/env python3
"""Monitor de tráfico gratuito — sin APIs de pago de Google."""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

from route_accident_bot_free.alert_reporter import format_alert, format_alert_telegram, format_ok_check
from route_accident_bot_free.news_investigator import Investigator
from route_accident_bot_free.nominatim_geocoder import LocationInfo, NominatimGeocoder
from route_accident_bot_free.ors_routes_client import OrsRoutesClient
from route_accident_bot_free.route_advisor import compare_routes, recommend
from route_accident_bot_free.telegram_notifier import TelegramNotifier
from route_accident_bot_free.tomtom_incidents_client import TomTomIncidentsClient
from route_accident_bot_free.traffic_analyzer import analyze_routes

SETTINGS_FILE = "RouteAccidentBotFree.Settings.yaml"
ENV_EXAMPLE_FILE = "RouteAccidentBotFree.env.example"


def load_config(config_path: Path) -> dict:
    with config_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    base_dir = Path(__file__).parent
    load_dotenv(base_dir / ".env", encoding="utf-8-sig")

    ors_key = os.getenv("ORS_API_KEY", "").strip()
    tomtom_key = os.getenv("TOMTOM_API_KEY", "").strip()
    nominatim_email = os.getenv("NOMINATIM_EMAIL", "").strip()

    if not ors_key:
        print("Error: define ORS_API_KEY en el archivo .env")
        print(f"Registro gratuito: https://openrouteservice.org/dev/#/signup")
        return 1

    if not tomtom_key:
        print("Error: define TOMTOM_API_KEY en el archivo .env")
        print(f"Registro gratuito: https://developer.tomtom.com/user/register")
        return 1

    config_path = base_dir / SETTINGS_FILE
    if not config_path.exists():
        print(f"Error: no se encontró {config_path}")
        return 1

    config = load_config(config_path)
    route_cfg = config.get("route", {})
    monitor_cfg = config.get("monitor", {})
    investigation_cfg = config.get("investigation", {})
    advisor_cfg = config.get("advisor", {})
    telegram_cfg = config.get("telegram", {})

    origin = route_cfg.get("origin", "").strip()
    destination = route_cfg.get("destination", "").strip()
    if not origin or not destination:
        print(f"Error: configura origin y destination en {SETTINGS_FILE}")
        return 1

    interval = int(monitor_cfg.get("interval_minutes", 45))
    delay_threshold = int(monitor_cfg.get("jam_delay_threshold_minutes", 13))
    cooldown = int(monitor_cfg.get("cooldown_minutes", 15))
    switch_threshold = int(advisor_cfg.get("recommend_switch_if_saves_minutes", 10))
    alternatives = int(advisor_cfg.get("alternative_routes", 2))
    language = investigation_cfg.get("language", "es")

    user_agent = f"RouteAccidentBotFree/1.0 ({nominatim_email or 'local'})"
    geocoder = NominatimGeocoder(user_agent=user_agent, email=nominatim_email)
    routes_client = OrsRoutesClient(ors_key)
    incidents_client = TomTomIncidentsClient(tomtom_key)
    investigator = Investigator(
        search_queries=investigation_cfg.get("search_queries", []),
        max_results=investigation_cfg.get("max_news_results", 5),
    )

    telegram = TelegramNotifier(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
    )
    telegram_enabled = telegram_cfg.get("enabled", False) and telegram.enabled
    notify_on_alert = telegram_cfg.get("notify_on_alert", True)
    notify_on_ok = telegram_cfg.get("notify_on_ok", False)

    print("=" * 50)
    print("  Route Accident Bot FREE")
    print("=" * 50)
    print(f"  Origen:      {origin}")
    print(f"  Destino:     {destination}")
    print(f"  Intervalo:   cada {interval} min")
    print(f"  Umbral:      +{delay_threshold} min")
    print(f"  APIs:        OpenRouteService + TomTom + Nominatim")
    print(f"  Telegram:    {'activo' if telegram_enabled else 'desactivado'}")
    print("  Ctrl+C para detener")
    print("=" * 50)
    print()

    origin_coords = geocoder.forward(origin)
    destination_coords = geocoder.forward(destination)
    if not origin_coords or not destination_coords:
        print("Error: no se pudo geocodificar origen o destino.")
        return 1

    last_alert_at: float | None = None

    try:
        while True:
            now = datetime.now()
            try:
                routes = routes_client.compute_routes(
                    origin_coords, destination_coords, alternatives=alternatives
                )

                if not routes:
                    print(f"[{now.strftime('%H:%M:%S')}] Sin rutas disponibles.")
                else:
                    all_coords: list[list[float]] = []
                    for route in routes:
                        all_coords.extend(route.get("coordinates", []))

                    incidents = incidents_client.fetch_incidents(all_coords)
                    analyses = analyze_routes(routes, incidents, delay_threshold)
                    primary = analyses[0]

                    if primary.has_severe_jam:
                        in_cooldown = (
                            last_alert_at is not None
                            and (time.time() - last_alert_at) < cooldown * 60
                        )

                        if in_cooldown:
                            print(
                                f"[{now.strftime('%H:%M:%S')}] Incidente detectado "
                                f"(cooldown {cooldown} min)"
                            )
                        else:
                            main_event = primary.events[0] if primary.events else None

                            if main_event:
                                location = geocoder.reverse(main_event.lat, main_event.lng)
                            else:
                                location = LocationInfo(
                                    formatted_address="Ubicacion no determinada",
                                    road="",
                                    neighborhood="",
                                    city="",
                                    state="",
                                )

                            news = investigator.search(location)
                            comparisons = compare_routes(analyses)
                            recommendation = recommend(
                                analyses, origin, destination, switch_threshold
                            )

                            print(
                                format_alert(
                                    timestamp=now,
                                    primary=primary,
                                    main_event=main_event,
                                    location=location,
                                    news=news,
                                    comparisons=comparisons,
                                    recommendation=recommendation,
                                )
                            )

                            if telegram_enabled and notify_on_alert:
                                try:
                                    telegram.send(
                                        format_alert_telegram(
                                            timestamp=now,
                                            primary=primary,
                                            main_event=main_event,
                                            location=location,
                                            news=news,
                                            comparisons=comparisons,
                                            recommendation=recommendation,
                                        )
                                    )
                                except Exception as exc:
                                    print(f"  Error de Telegram: {exc}")

                            last_alert_at = time.time()
                    else:
                        ok_text = format_ok_check(now, primary)
                        print(ok_text)
                        if telegram_enabled and notify_on_ok:
                            try:
                                telegram.send(ok_text, parse_mode=None)
                            except Exception:
                                pass

            except requests.HTTPError as exc:
                print(f"[{now.strftime('%H:%M:%S')}] Error HTTP: {exc}")
                if exc.response is not None:
                    print(f"  Detalle: {exc.response.text[:300]}")
            except Exception as exc:
                print(f"[{now.strftime('%H:%M:%S')}] Error: {exc}")

            time.sleep(interval * 60)

    except KeyboardInterrupt:
        print("\nMonitoreo detenido.")
        return 0


if __name__ == "__main__":
    sys.exit(main())