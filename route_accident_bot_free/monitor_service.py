"""Servicio de analisis de rutas con APIs gratuitas."""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from .alert_reporter import format_alert, format_alert_telegram, format_ok_check
from .config_state import SETTINGS_FILE, load_config, save_config
from .news_investigator import Investigator
from .nominatim_geocoder import LocationInfo, NominatimGeocoder
from .ors_routes_client import OrsRoutesClient
from .route_advisor import compare_routes, recommend
from .telegram_notifier import TelegramNotifier
from .tomtom_incidents_client import TomTomIncidentsClient
from .traffic_analyzer import analyze_routes

__all__ = ["RouteMonitor", "load_config", "save_config", "SETTINGS_FILE"]


class RouteMonitor:
    def __init__(
        self,
        base_dir: Path,
        config: dict[str, Any],
        on_log: Callable[[str], None] | None = None,
        on_status: Callable[[str], None] | None = None,
        origin_coords: tuple[float, float] | None = None,
        destination_coords: tuple[float, float] | None = None,
    ):
        self.base_dir = base_dir
        self.config = config
        self.on_log = on_log or print
        self.on_status = on_status or (lambda _: None)
        self.origin_coords_override = origin_coords
        self.destination_coords_override = destination_coords

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_alert_at: float | None = None
        self._route_note_shown = False
        self._periodic = False

        load_dotenv(base_dir / ".env", encoding="utf-8-sig")
        self._init_clients()

    def _init_clients(self) -> None:
        route_cfg = self.config.get("route", {})
        investigation_cfg = self.config.get("investigation", {})
        advisor_cfg = self.config.get("advisor", {})
        telegram_cfg = self.config.get("telegram", {})

        ors_key = os.getenv("ORS_API_KEY", "").strip()
        tomtom_key = os.getenv("TOMTOM_API_KEY", "").strip()
        nominatim_email = os.getenv("NOMINATIM_EMAIL", "").strip()
        if not ors_key:
            raise ValueError("Define ORS_API_KEY en el archivo .env")
        if not tomtom_key:
            raise ValueError("Define TOMTOM_API_KEY en el archivo .env")

        self.origin = route_cfg.get("origin", "").strip()
        self.destination = route_cfg.get("destination", "").strip()
        if not self.origin or not self.destination:
            raise ValueError("Configura la ruta con un enlace de Google Maps")

        monitor_cfg = self.config.get("monitor", {})
        self.interval = int(monitor_cfg.get("interval_minutes", 45))
        self.delay_threshold = int(monitor_cfg.get("jam_delay_threshold_minutes", 13))
        self.cooldown = int(monitor_cfg.get("cooldown_minutes", 15))
        self.switch_threshold = int(advisor_cfg.get("recommend_switch_if_saves_minutes", 10))
        self.alternatives = int(advisor_cfg.get("alternative_routes", 2))
        self.road_preference = route_cfg.get("road_preference", "free")
        self.avoid_tolls = self.road_preference == "free"

        user_agent = f"RouteAccidentBotFree/1.0 ({nominatim_email or 'local'})"
        self.geocoder = NominatimGeocoder(user_agent=user_agent, email=nominatim_email)
        self.routes_client = OrsRoutesClient(ors_key)
        self.incidents_client = TomTomIncidentsClient(tomtom_key)
        self.investigator = Investigator(
            search_queries=investigation_cfg.get("search_queries", []),
            max_results=investigation_cfg.get("max_news_results", 5),
        )
        self.telegram = TelegramNotifier(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        )
        self.telegram_enabled = telegram_cfg.get("enabled", False) and self.telegram.enabled
        self.notify_on_alert = telegram_cfg.get("notify_on_alert", True)
        self.notify_on_ok = telegram_cfg.get("notify_on_ok", False)

        self.origin_coords = self._resolve_coords(self.origin_coords_override, self.origin)
        self.destination_coords = self._resolve_coords(self.destination_coords_override, self.destination)
        if not self.origin_coords or not self.destination_coords:
            raise ValueError("No se pudo geocodificar origen o destino.")

    def _resolve_coords(
        self,
        override: tuple[float, float] | None,
        label: str,
    ) -> tuple[float, float] | None:
        if override:
            return override
        coords = self.geocoder.forward(label)
        if coords:
            return coords
        return self._parse_coord_label(label)

    @staticmethod
    def _parse_coord_label(label: str) -> tuple[float, float] | None:
        if "," not in label:
            return None
        parts = [part.strip() for part in label.split(",", 1)]
        if len(parts) != 2:
            return None
        try:
            return float(parts[0]), float(parts[1])
        except ValueError:
            return None

    def _log(self, message: str) -> None:
        self.on_log(message)

    def _road_label(self) -> str:
        return "Libre (sin cuota)" if self.road_preference == "free" else "Cuota"

    def print_banner(self) -> None:
        self._log("=" * 50)
        self._log("  Route Accident Bot FREE - Analisis de ruta")
        self._log("=" * 50)
        self._log(f"  Origen:      {self.origin}")
        self._log(f"  Destino:     {self.destination}")
        self._log(f"  Carretera:   {self._road_label()}")
        self._log(f"  Telegram:    {'activo' if self.telegram_enabled else 'desactivado'}")
        self._log("=" * 50)
        self._log("")

    def run_once(self) -> None:
        now = datetime.now()
        try:
            routes = self.routes_client.compute_routes(
                self.origin_coords,
                self.destination_coords,
                alternatives=self.alternatives,
                avoid_tolls=self.avoid_tolls,
            )

            if self.routes_client.last_route_note and not self._route_note_shown:
                self._log(f"  Nota: {self.routes_client.last_route_note}")
                self._route_note_shown = True

            if not routes:
                self._log(f"[{now.strftime('%H:%M:%S')}] Sin rutas disponibles.")
                return

            all_coords: list[list[float]] = []
            for route in routes:
                all_coords.extend(route.get("coordinates", []))

            incidents = self.incidents_client.fetch_incidents(all_coords)
            analyses = analyze_routes(routes, incidents, self.delay_threshold)
            primary = analyses[0]

            if primary.has_severe_jam:
                in_cooldown = (
                    self._last_alert_at is not None
                    and (time.time() - self._last_alert_at) < self.cooldown * 60
                )

                if in_cooldown:
                    self._log(
                        f"[{now.strftime('%H:%M:%S')}] Incidente detectado "
                        f"(cooldown {self.cooldown} min)"
                    )
                else:
                    main_event = primary.events[0] if primary.events else None

                    if main_event:
                        location = self.geocoder.reverse(main_event.lat, main_event.lng)
                    else:
                        location = LocationInfo(
                            formatted_address="Ubicacion no determinada",
                            road="",
                            neighborhood="",
                            city="",
                            state="",
                        )

                    news = self.investigator.search(location)
                    comparisons = compare_routes(analyses)
                    recommendation = recommend(
                        analyses, self.origin, self.destination, self.switch_threshold
                    )

                    self._log(
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

                    if self.telegram_enabled and self.notify_on_alert:
                        try:
                            self.telegram.send(
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
                            self._log(f"  Error de Telegram: {exc}")

                    self._last_alert_at = time.time()
            else:
                ok_text = format_ok_check(now, primary)
                self._log(ok_text)
                if self.telegram_enabled and self.notify_on_ok:
                    try:
                        self.telegram.send(ok_text, parse_mode=None)
                    except Exception:
                        pass

        except requests.HTTPError as exc:
            self._log(f"[{now.strftime('%H:%M:%S')}] Error HTTP: {exc}")
            if exc.response is not None:
                self._log(f"  Detalle: {exc.response.text[:300]}")
        except Exception as exc:
            self._log(f"[{now.strftime('%H:%M:%S')}] Error: {exc}")

    def _analysis_loop(self) -> None:
        self.on_status("Analizando")
        self.run_once()

        if not self._periodic:
            self.on_status("Detenido")
            return

        while not self._stop_event.is_set():
            self.on_status("Esperando proxima revision")
            if self._stop_event.wait(self.interval * 60):
                break
            self.on_status("Analizando")
            self.run_once()

        self.on_status("Detenido")

    def start_analysis(self, periodic: bool) -> None:
        self.stop()
        self._periodic = periodic
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None
        self.on_status("Detenido")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()