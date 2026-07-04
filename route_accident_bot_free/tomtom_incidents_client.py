"""Incidentes de tráfico gratuitos con TomTom (tier gratuito)."""

from __future__ import annotations

from dataclasses import dataclass

import requests

INCIDENTS_URL = "https://api.tomtom.com/traffic/services/5/incidentDetails"
MAX_BBOX_SPAN_DEG = 0.45


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

    def _chunk_coordinates(self, coordinates: list[list[float]]) -> list[list[list[float]]]:
        if len(coordinates) <= 2:
            return [coordinates]

        lngs = [c[0] for c in coordinates]
        lats = [c[1] for c in coordinates]
        lng_span = max(lngs) - min(lngs)
        lat_span = max(lats) - min(lats)

        if lng_span <= MAX_BBOX_SPAN_DEG and lat_span <= MAX_BBOX_SPAN_DEG:
            return [coordinates]

        chunk_count = max(
            int(lng_span / MAX_BBOX_SPAN_DEG) + 1,
            int(lat_span / MAX_BBOX_SPAN_DEG) + 1,
            2,
        )
        chunk_size = max(len(coordinates) // chunk_count, 2)
        chunks = []
        for i in range(0, len(coordinates), chunk_size):
            chunk = coordinates[i : i + chunk_size]
            if len(chunk) >= 2:
                chunks.append(chunk)
        return chunks or [coordinates]

    def _fetch_bbox(self, coordinates: list[list[float]]) -> list[TrafficIncident]:
        lngs = [c[0] for c in coordinates]
        lats = [c[1] for c in coordinates]
        padding = 0.015
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
            description = (
                events[0].get("description", "Incidente de tráfico")
                if events
                else "Incidente de tráfico"
            )
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

    def fetch_incidents(self, coordinates: list[list[float]]) -> list[TrafficIncident]:
        if not coordinates or not self.api_key:
            return []

        seen: set[str] = set()
        merged: list[TrafficIncident] = []

        for chunk in self._chunk_coordinates(coordinates):
            for incident in self._fetch_bbox(chunk):
                if incident.id in seen:
                    continue
                seen.add(incident.id)
                merged.append(incident)

        return merged