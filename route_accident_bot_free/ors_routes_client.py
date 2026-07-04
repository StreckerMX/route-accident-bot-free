"""Cliente gratuito para OpenRouteService."""

from __future__ import annotations

import math
from typing import Any

import requests

ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
MAX_ALTERNATIVES_DISTANCE_KM = 95.0


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


class OrsRoutesClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.last_route_note = ""

    def _request_routes(
        self,
        origin: list[float],
        destination: list[float],
        alternatives: int,
        avoid_tolls: bool = False,
    ) -> requests.Response:
        body: dict[str, Any] = {
            "coordinates": [origin, destination],
            "language": "es",
            "units": "km",
        }
        if avoid_tolls:
            body["options"] = {"avoid_features": ["tollways"]}
        if alternatives > 0:
            body["alternative_routes"] = {
                "target_count": alternatives,
                "share_factor": 0.6,
                "weight_factor": 1.4,
            }

        return requests.post(
            ORS_URL,
            json=body,
            headers={"Authorization": self.api_key, "Content-Type": "application/json"},
            timeout=45,
        )

    def compute_routes(
        self,
        origin_coords: tuple[float, float],
        destination_coords: tuple[float, float],
        alternatives: int = 2,
        avoid_tolls: bool = False,
    ) -> list[dict[str, Any]]:
        origin = [origin_coords[1], origin_coords[0]]
        destination = [destination_coords[1], destination_coords[0]]
        self.last_route_note = ""

        straight_km = _haversine_km(
            origin_coords[0], origin_coords[1],
            destination_coords[0], destination_coords[1],
        )

        use_alternatives = alternatives
        if straight_km > MAX_ALTERNATIVES_DISTANCE_KM:
            use_alternatives = 0
            self.last_route_note = (
                f"Ruta larga (~{straight_km:.0f} km): sin alternativas "
                f"(limite gratuito ORS: 100 km)."
            )

        response = self._request_routes(origin, destination, use_alternatives, avoid_tolls)

        if response.status_code == 400 and use_alternatives > 0:
            try:
                error_code = response.json().get("error", {}).get("code")
            except Exception:
                error_code = None
            if error_code == 2004:
                use_alternatives = 0
                self.last_route_note = "Ruta demasiado larga para alternativas ORS. Usando ruta unica."
                response = self._request_routes(origin, destination, 0, avoid_tolls)

        response.raise_for_status()
        data = response.json()

        routes = []
        for i, feature in enumerate(data.get("features", [])):
            props = feature.get("properties", {})
            summary = props.get("summary", {})
            geometry = feature.get("geometry", {})
            routes.append(
                {
                    "index": i,
                    "duration_seconds": int(summary.get("duration", 0)),
                    "distance_km": round(summary.get("distance", 0), 1),
                    "coordinates": geometry.get("coordinates", []),
                }
            )
        return routes

    @staticmethod
    def route_label(index: int) -> str:
        if index == 0:
            return "Ruta principal"
        return f"Alternativa {index}"

    @staticmethod
    def duration_minutes(route: dict[str, Any]) -> int:
        return route.get("duration_seconds", 0) // 60