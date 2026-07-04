"""Incidentes de tráfico gratuitos con TomTom (tier gratuito)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

INCIDENTS_URL = "https://api.tomtom.com/traffic/services/5/incidentDetails"


@dataclass
class TrafficIncident:
    id: str
    type: str
    description: str
    severity: str
    lat: float
    lng: float
    delay_minutes: int


class TomTomIncidentsClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch_incidents(self, coordinates: list[list[float]]) -> list[TrafficIncident]:
        if not coordinates or not self.api_key:
            return []

        lngs = [c[0] for c in coordinates]
        lats = [c[1] for c in coordinates]
        padding = 0.08
        bbox = f"{min(lngs) - padding},{min(lats) - padding},{max(lngs) + padding},{max(lats) + padding}"

        response = requests.get(
            INCIDENTS_URL,
            params={
                "key": self.api_key,
                "bbox": bbox,
                "fields": (
                    "{incidents{type,geometry{type,coordinates},"
                    "properties{id,iconCategory,magnitudeOfDelay,events{description}}}}"
                ),
                "language": "es-ES",
            },
            timeout=25,
        )
        response.raise_for_status()
        data = response.json()

        incidents: list[TrafficIncident] = []
        for item in data.get("incidents", []):
            props = item.get("properties", {})
            geometry = item.get("geometry", {})
            coords = geometry.get("coordinates", [])
            if not coords:
                continue

            if geometry.get("type") == "Point":
                lng, lat = coords[0], coords[1]
            else:
                lng, lat = coords[0][0], coords[0][1]

            events = props.get("events", [])
            description = events[0].get("description", "Incidente de tráfico") if events else "Incidente"
            magnitude = int(props.get("magnitudeOfDelay", 0) or 0)
            icon = int(props.get("iconCategory", 0) or 0)

            severity = "BAJA"
            if magnitude >= 3 or icon in (1, 2, 6):
                severity = "ALTA"
            elif magnitude >= 1:
                severity = "MEDIA"

            incidents.append(
                TrafficIncident(
                    id=str(props.get("id", "")),
                    type=str(item.get("type", "incident")),
                    description=description,
                    severity=severity,
                    lat=lat,
                    lng=lng,
                    delay_minutes=max(magnitude * 4, 0),
                )
            )

        return incidents