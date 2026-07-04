"""Analiza rutas e incidentes para detectar alertas."""

from __future__ import annotations

from dataclasses import dataclass, field

from .ors_routes_client import OrsRoutesClient
from .tomtom_incidents_client import TrafficIncident


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


def analyze_routes(
    routes: list[dict],
    incidents: list[TrafficIncident],
    delay_threshold_minutes: int,
) -> list[RouteAnalysis]:
    if not routes:
        return []

    durations = [OrsRoutesClient.duration_minutes(r) for r in routes]
    fastest = min(durations)
    events = _incidents_to_events(incidents)
    max_incident_delay = max((i.delay_minutes for i in incidents), default=0)
    has_major_incident = any(i.severity == "ALTA" for i in incidents)

    analyses: list[RouteAnalysis] = []
    for route in routes:
        duration = OrsRoutesClient.duration_minutes(route)
        route_delay = max(0, duration - fastest)
        effective_delay = max(route_delay, max_incident_delay)

        has_severe = bool(incidents) and (
            has_major_incident
            or effective_delay >= delay_threshold_minutes
            or any(i.severity == "MEDIA" and i.delay_minutes >= delay_threshold_minutes for i in incidents)
        )

        analyses.append(
            RouteAnalysis(
                route_index=route["index"],
                route_label=OrsRoutesClient.route_label(route["index"]),
                duration_minutes=duration,
                delay_minutes=effective_delay,
                distance_km=route.get("distance_km", 0),
                warnings=[inc.description for inc in incidents[:3]],
                events=events,
                has_severe_jam=has_severe,
            )
        )

    return analyses