"""Analiza rutas e incidentes para detectar alertas."""

from __future__ import annotations

from dataclasses import dataclass, field

from .ors_routes_client import OrsRoutesClient
from .route_geometry import point_to_polyline_distance_km
from .tomtom_incidents_client import TrafficIncident

MAX_INCIDENT_DISTANCE_KM = 2.0


@dataclass
class TrafficEvent:
    speed: str
    lat: float
    lng: float
    road_hint: str = ""
    severity: str = "BAJA"
    description: str = ""


@dataclass
class RouteAnalysis:
    route_index: int
    route_label: str
    duration_minutes: int
    delay_minutes: int
    distance_km: float
    warnings: list[str] = field(default_factory=list)
    events: list[TrafficEvent] = field(default_factory=list)
    has_severe_jam: bool = False


def _incidents_to_events(incidents: list[TrafficIncident]) -> list[TrafficEvent]:
    events = []
    for inc in incidents:
        events.append(
            TrafficEvent(
                speed="TRAFFIC_JAM" if inc.severity == "ALTA" else "SLOW",
                lat=inc.lat,
                lng=inc.lng,
                road_hint=inc.description[:120],
                severity=inc.severity,
                description=inc.description,
            )
        )
    return events


def _incidents_on_route(
    incidents: list[TrafficIncident],
    coordinates: list[list[float]],
    max_distance_km: float = MAX_INCIDENT_DISTANCE_KM,
) -> list[TrafficIncident]:
    if not coordinates:
        return []
    return [
        incident
        for incident in incidents
        if point_to_polyline_distance_km(incident.lat, incident.lng, coordinates) <= max_distance_km
    ]


def pick_main_event(events: list[TrafficEvent], coordinates: list[list[float]]) -> TrafficEvent | None:
    if not events:
        return None
    severity_rank = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
    return sorted(
        events,
        key=lambda event: (
            severity_rank.get(event.severity, 9),
            point_to_polyline_distance_km(event.lat, event.lng, coordinates),
        ),
    )[0]


def analyze_routes(
    routes: list[dict],
    incidents: list[TrafficIncident],
    delay_threshold_minutes: int,
) -> list[RouteAnalysis]:
    if not routes:
        return []

    durations = [OrsRoutesClient.duration_minutes(r) for r in routes]
    fastest = min(durations)

    analyses: list[RouteAnalysis] = []
    for route in routes:
        coordinates = route.get("coordinates", [])
        route_incidents = _incidents_on_route(incidents, coordinates)
        events = _incidents_to_events(route_incidents)

        duration = OrsRoutesClient.duration_minutes(route)
        route_delay = max(0, duration - fastest)
        max_incident_delay = max((inc.delay_minutes for inc in route_incidents), default=0)
        has_major_incident = any(inc.severity == "ALTA" for inc in route_incidents)
        has_medium_delay = any(
            inc.severity == "MEDIA" and inc.delay_minutes >= delay_threshold_minutes
            for inc in route_incidents
        )

        effective_delay = max(route_delay, max_incident_delay) if route_incidents else route_delay
        has_severe = (
            effective_delay >= delay_threshold_minutes
            or has_major_incident
            or has_medium_delay
        )

        analyses.append(
            RouteAnalysis(
                route_index=route["index"],
                route_label=OrsRoutesClient.route_label(route["index"]),
                duration_minutes=duration,
                delay_minutes=effective_delay,
                distance_km=route.get("distance_km", 0),
                warnings=[inc.description for inc in route_incidents[:3]],
                events=events,
                has_severe_jam=has_severe,
            )
        )

    return analyses