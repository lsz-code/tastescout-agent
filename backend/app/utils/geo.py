from math import asin, cos, radians, sin, sqrt
from typing import Any

from pydantic import BaseModel


EARTH_RADIUS_METERS = 6_371_000


def parse_location(location: Any) -> dict[str, float] | None:
    if location is None:
        return None

    if isinstance(location, str):
        return _parse_location_string(location)

    if isinstance(location, BaseModel):
        location = location.model_dump()

    if isinstance(location, dict):
        return _parse_location_mapping(location)

    longitude = getattr(location, "longitude", None)
    latitude = getattr(location, "latitude", None)
    if longitude is None or latitude is None:
        longitude = getattr(location, "lng", None)
        latitude = getattr(location, "lat", None)

    return _build_location(longitude, latitude)


def calculate_distance_meters(origin: Any, destination: Any) -> float | None:
    parsed_origin = parse_location(origin)
    parsed_destination = parse_location(destination)
    if parsed_origin is None or parsed_destination is None:
        return None

    origin_lng = radians(parsed_origin["longitude"])
    origin_lat = radians(parsed_origin["latitude"])
    destination_lng = radians(parsed_destination["longitude"])
    destination_lat = radians(parsed_destination["latitude"])

    delta_lng = destination_lng - origin_lng
    delta_lat = destination_lat - origin_lat

    haversine = (
        sin(delta_lat / 2) ** 2
        + cos(origin_lat) * cos(destination_lat) * sin(delta_lng / 2) ** 2
    )
    distance = 2 * EARTH_RADIUS_METERS * asin(sqrt(haversine))
    return round(distance, 1)


def _parse_location_string(location: str) -> dict[str, float] | None:
    if "," not in location:
        return None

    longitude, latitude = location.split(",", maxsplit=1)
    return _build_location(longitude.strip(), latitude.strip())


def _parse_location_mapping(location: dict[str, Any]) -> dict[str, float] | None:
    longitude = location.get("longitude")
    latitude = location.get("latitude")
    if longitude is None or latitude is None:
        longitude = location.get("lng")
        latitude = location.get("lat")

    return _build_location(longitude, latitude)


def _build_location(longitude: Any, latitude: Any) -> dict[str, float] | None:
    if longitude is None or latitude is None:
        return None

    try:
        return {
            "longitude": float(longitude),
            "latitude": float(latitude),
        }
    except (TypeError, ValueError):
        return None
