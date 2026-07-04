"""Cliente gratuito para OpenRouteService."""

from __future__ import annotations

from typing import Any

import requests

ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/json"


class OrsRoutesClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def compute_routes(
        self,
        origin_coords: tuple[float, float],
        destination_coords: tuple[float, float],
        alternatives: int = 2,
    ) -> list[dict[str, Any]]:
        origin = [origin_coords[1], origin_coords[0]]
        destination = [destination_coords[1], destination_coords[0]]

        body: dict[str, Any] = {
            "coordinates": [origin, destination],
            "language": "es",
            "units": "km",
        }
        if alternatives > 0:
            body["alternative_routes"] = {
                "target_count": alternatives,
                "share_factor": 0.6,
                "weight_factor": 1.4,
            }

        response = requests.post(
            ORS_URL,
            json=body,
            headers={"Authorization": self.api_key, "Content-Type": "application/json"},
            timeout=30,
        )
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