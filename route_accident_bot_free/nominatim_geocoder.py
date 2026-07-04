"""Geocodificación gratuita con OpenStreetMap Nominatim."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
_LAST_REQUEST = 0.0


@dataclass
class LocationInfo:
    formatted_address: str
    road: str
    neighborhood: str
    city: str
    state: str


class NominatimGeocoder:
    def __init__(self, user_agent: str, email: str = ""):
        self.headers = {"User-Agent": user_agent}
        if email:
            self.headers["From"] = email

    def _throttle(self) -> None:
        global _LAST_REQUEST
        elapsed = time.time() - _LAST_REQUEST
        if elapsed < 1.1:
            time.sleep(1.1 - elapsed)
        _LAST_REQUEST = time.time()

    def forward(self, query: str) -> tuple[float, float] | None:
        self._throttle()
        response = requests.get(
            f"{NOMINATIM_URL}/search",
            params={"q": query, "format": "json", "limit": 1},
            headers=self.headers,
            timeout=20,
        )
        response.raise_for_status()
        results = response.json()
        if not results:
            return None
        return float(results[0]["lat"]), float(results[0]["lon"])

    def reverse(self, lat: float, lng: float) -> LocationInfo:
        self._throttle()
        response = requests.get(
            f"{NOMINATIM_URL}/reverse",
            params={"lat": lat, "lon": lng, "format": "json", "addressdetails": 1},
            headers=self.headers,
            timeout=20,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        address = data.get("address", {})

        return LocationInfo(
            formatted_address=data.get("display_name", f"{lat:.5f}, {lng:.5f}"),
            road=address.get("road", address.get("pedestrian", "")),
            neighborhood=address.get("suburb", address.get("neighbourhood", "")),
            city=address.get("city", address.get("town", address.get("state", ""))),
            state=address.get("state", ""),
        )