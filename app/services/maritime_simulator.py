import math
import time

from app.models.asset import Asset, AssetStatus, AssetType
from app.models.telemetry import Telemetry
from app.services.maritime_events import get_maritime_events


SIMULATION_TIME_SCALE = 8.0

_DRONE_START_LATITUDE = 41.3600
_DRONE_START_LONGITUDE = 2.2250

_BOAT_START_LATITUDE = 41.3510
_BOAT_START_LONGITUDE = 2.2150

_DRONE_SPEED_MPS = 16.0
_BOAT_SPEED_MPS = 8.0

_MISSION_START_TIME: float | None = None


def reset_maritime_simulation() -> None:
    global _MISSION_START_TIME

    _MISSION_START_TIME = time.monotonic()


def get_maritime_assets() -> list[Asset]:
    global _MISSION_START_TIME

    if _MISSION_START_TIME is None:
        reset_maritime_simulation()

    if _MISSION_START_TIME is None:
        return []

    current_time = time.monotonic()

    real_elapsed_seconds = (
        current_time - _MISSION_START_TIME
    )

    simulated_elapsed_seconds = (
        real_elapsed_seconds * SIMULATION_TIME_SCALE
    )

    events = get_maritime_events()

    if not events:
        return []

    target_event = events[0]

    drone = _create_sar_drone(
        elapsed_seconds=simulated_elapsed_seconds,
        real_elapsed_seconds=real_elapsed_seconds,
        target_latitude=target_event.latitude,
        target_longitude=target_event.longitude,
    )

    boat = _create_rescue_boat(
        elapsed_seconds=simulated_elapsed_seconds,
        real_elapsed_seconds=real_elapsed_seconds,
        target_latitude=target_event.latitude,
        target_longitude=target_event.longitude,
    )

    return [
        drone,
        boat,
    ]


def _create_sar_drone(
    elapsed_seconds: float,
    real_elapsed_seconds: float,
    target_latitude: float,
    target_longitude: float,
) -> Asset:
    (
        latitude,
        longitude,
        heading,
        arrived,
    ) = _move_towards_target(
        start_latitude=_DRONE_START_LATITUDE,
        start_longitude=_DRONE_START_LONGITUDE,
        target_latitude=target_latitude,
        target_longitude=target_longitude,
        speed_mps=_DRONE_SPEED_MPS,
        elapsed_seconds=elapsed_seconds,
        arrival_radius_meters=20.0,
    )

    return Asset(
        id="sar-drone-001",
        name="SAR Drone One",
        asset_type=AssetType.AERIAL_DRONE,
        status=AssetStatus.ACTIVE,
        battery=max(
            0,
            int(94 - real_elapsed_seconds / 180),
        ),
        telemetry=Telemetry(
            latitude=latitude,
            longitude=longitude,
            altitude=70.0 if arrived else 85.0,
            speed=0.0 if arrived else _DRONE_SPEED_MPS,
            heading=heading,
        ),
    )


def _create_rescue_boat(
    elapsed_seconds: float,
    real_elapsed_seconds: float,
    target_latitude: float,
    target_longitude: float,
) -> Asset:
    (
        latitude,
        longitude,
        heading,
        arrived,
    ) = _move_towards_target(
        start_latitude=_BOAT_START_LATITUDE,
        start_longitude=_BOAT_START_LONGITUDE,
        target_latitude=target_latitude,
        target_longitude=target_longitude,
        speed_mps=_BOAT_SPEED_MPS,
        elapsed_seconds=elapsed_seconds,
        arrival_radius_meters=15.0,
    )

    return Asset(
        id="rescue-boat-001",
        name="Rescue Boat One",
        asset_type=AssetType.MARITIME_VEHICLE,
        status=(
            AssetStatus.ACTIVE
            if not arrived
            else AssetStatus.READY
        ),
        battery=max(
            0,
            int(88 - real_elapsed_seconds / 300),
        ),
        telemetry=Telemetry(
            latitude=latitude,
            longitude=longitude,
            altitude=0.0,
            speed=0.0 if arrived else _BOAT_SPEED_MPS,
            heading=heading,
        ),
    )


def _move_towards_target(
    start_latitude: float,
    start_longitude: float,
    target_latitude: float,
    target_longitude: float,
    speed_mps: float,
    elapsed_seconds: float,
    arrival_radius_meters: float,
) -> tuple[float, float, float, bool]:
    total_distance_meters = _calculate_distance_meters(
        latitude_1=start_latitude,
        longitude_1=start_longitude,
        latitude_2=target_latitude,
        longitude_2=target_longitude,
    )

    heading = _calculate_heading(
        latitude_1=start_latitude,
        longitude_1=start_longitude,
        latitude_2=target_latitude,
        longitude_2=target_longitude,
    )

    if total_distance_meters <= arrival_radius_meters:
        return (
            round(target_latitude, 6),
            round(target_longitude, 6),
            round(heading, 2),
            True,
        )

    travelled_meters = min(
        speed_mps * elapsed_seconds,
        total_distance_meters,
    )

    progress = travelled_meters / total_distance_meters

    latitude = (
        start_latitude
        + (
            target_latitude - start_latitude
        )
        * progress
    )

    longitude = (
        start_longitude
        + (
            target_longitude - start_longitude
        )
        * progress
    )

    remaining_distance_meters = (
        total_distance_meters - travelled_meters
    )

    arrived = (
        remaining_distance_meters
        <= arrival_radius_meters
    )

    if arrived:
        latitude = target_latitude
        longitude = target_longitude

    return (
        round(latitude, 6),
        round(longitude, 6),
        round(heading, 2),
        arrived,
    )


def _calculate_distance_meters(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    earth_radius_meters = 6_371_000.0

    latitude_1_radians = math.radians(latitude_1)
    latitude_2_radians = math.radians(latitude_2)

    latitude_delta = math.radians(
        latitude_2 - latitude_1
    )

    longitude_delta = math.radians(
        longitude_2 - longitude_1
    )

    haversine_value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_1_radians)
        * math.cos(latitude_2_radians)
        * math.sin(longitude_delta / 2) ** 2
    )

    angular_distance = 2 * math.atan2(
        math.sqrt(haversine_value),
        math.sqrt(1 - haversine_value),
    )

    return earth_radius_meters * angular_distance


def _calculate_heading(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    latitude_1_radians = math.radians(latitude_1)
    latitude_2_radians = math.radians(latitude_2)

    longitude_delta = math.radians(
        longitude_2 - longitude_1
    )

    x_value = math.sin(longitude_delta) * math.cos(
        latitude_2_radians
    )

    y_value = (
        math.cos(latitude_1_radians)
        * math.sin(latitude_2_radians)
        - math.sin(latitude_1_radians)
        * math.cos(latitude_2_radians)
        * math.cos(longitude_delta)
    )

    heading = math.degrees(
        math.atan2(x_value, y_value)
    )

    return (heading + 360) % 360