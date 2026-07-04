"""Utilidades geometricas para validar puntos sobre una ruta."""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0
MAX_INCIDENT_DISTANCE_KM = 0.05  # 50 metros


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _to_xy_km(lat: float, lng: float, ref_lat: float) -> tuple[float, float]:
    x = math.radians(lng) * EARTH_RADIUS_KM * math.cos(math.radians(ref_lat))
    y = math.radians(lat) * EARTH_RADIUS_KM
    return x, y


def _point_segment_distance_km(
    lat: float,
    lng: float,
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
) -> float:
    ref_lat = (lat + lat1 + lat2) / 3
    px, py = _to_xy_km(lat, lng, ref_lat)
    x1, y1 = _to_xy_km(lat1, lng1, ref_lat)
    x2, y2 = _to_xy_km(lat2, lng2, ref_lat)

    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)

    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def point_to_polyline_distance_km(
    lat: float,
    lng: float,
    coordinates: list[list[float]],
) -> float:
    """Distancia minima de un punto a una polyline ORS/GeoJSON [lng, lat]."""
    if not coordinates:
        return float("inf")
    if len(coordinates) == 1:
        lng0, lat0 = coordinates[0]
        return haversine_km(lat, lng, lat0, lng0)

    min_dist = float("inf")
    for i in range(len(coordinates) - 1):
        lng1, lat1 = coordinates[i]
        lng2, lat2 = coordinates[i + 1]
        dist = _point_segment_distance_km(lat, lng, lat1, lng1, lat2, lng2)
        min_dist = min(min_dist, dist)
    return min_dist


def filter_points_near_polyline(
    points: list[dict],
    coordinates: list[list[float]],
    max_distance_km: float = 2.0,
    lat_key: str = "lat",
    lng_key: str = "lng",
) -> list[dict]:
    if not coordinates:
        return points
    return [
        point
        for point in points
        if point_to_polyline_distance_km(point[lat_key], point[lng_key], coordinates) <= max_distance_km
    ]