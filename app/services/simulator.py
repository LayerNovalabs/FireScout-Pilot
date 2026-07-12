import math
import time

from app.models.asset import Asset, AssetStatus, AssetType
from app.models.telemetry import Telemetry


_START_TIME = time.monotonic()


def get_simulated_assets() -> list[Asset]:
    elapsed = time.monotonic() - _START_TIME

    return [
        _create_alpha(elapsed),
        _create_bravo(elapsed),
        _create_charlie(elapsed),
    ]


def _create_alpha(elapsed: float) -> Asset:
    angle = elapsed * 0.08

    latitude = 41.3885 + 0.0018 * math.sin(angle)
    longitude = 2.1705 + 0.0024 * math.cos(angle)

    latitude_speed = 0.0018 * 0.08 * math.cos(angle)
    longitude_speed = -0.0024 * 0.08 * math.sin(angle)

    return _build_asset(
        asset_id="sim-001",
        name="Simulator Alpha",
        starting_battery=92,
        elapsed=elapsed,
        latitude=latitude,
        longitude=longitude,
        altitude=120.0 + 4.0 * math.sin(elapsed / 5.0),
        speed=14.5 + 1.2 * math.sin(elapsed / 3.0),
        heading=_calculate_heading(
            latitude_speed,
            longitude_speed,
        ),
    )


def _create_bravo(elapsed: float) -> Asset:
    latitude_angle = elapsed * 0.045
    longitude_angle = elapsed * 0.025

    latitude = 41.3905 + 0.0013 * math.sin(latitude_angle)
    longitude = 2.1645 + 0.0038 * math.sin(longitude_angle)

    latitude_speed = (
        0.0013
        * 0.045
        * math.cos(latitude_angle)
    )

    longitude_speed = (
        0.0038
        * 0.025
        * math.cos(longitude_angle)
    )

    return _build_asset(
        asset_id="sim-002",
        name="Simulator Bravo",
        starting_battery=84,
        elapsed=elapsed,
        latitude=latitude,
        longitude=longitude,
        altitude=105.0 + 3.0 * math.sin(elapsed / 6.0),
        speed=12.8 + 1.0 * math.cos(elapsed / 4.0),
        heading=_calculate_heading(
            latitude_speed,
            longitude_speed,
        ),
    )


def _create_charlie(elapsed: float) -> Asset:
    angle = elapsed * 0.055

    latitude = 41.3848 + 0.0023 * math.sin(angle)

    longitude = (
        2.1670
        + 0.0032
        * math.sin(angle)
        * math.cos(angle)
    )

    latitude_speed = (
        0.0023
        * 0.055
        * math.cos(angle)
    )

    longitude_speed = (
        0.0032
        * 0.055
        * math.cos(2.0 * angle)
    )

    return _build_asset(
        asset_id="sim-003",
        name="Simulator Charlie",
        starting_battery=28,
        elapsed=elapsed,
        latitude=latitude,
        longitude=longitude,
        altitude=95.0 + 2.5 * math.sin(elapsed / 4.0),
        speed=10.2 + 0.8 * math.sin(elapsed / 3.5),
        heading=_calculate_heading(
            latitude_speed,
            longitude_speed,
        ),
    )


def _build_asset(
    asset_id: str,
    name: str,
    starting_battery: int,
    elapsed: float,
    latitude: float,
    longitude: float,
    altitude: float,
    speed: float,
    heading: float,
) -> Asset:
    battery = max(
        0,
        int(starting_battery - elapsed / 120),
    )

    status = (
        AssetStatus.WARNING
        if battery <= 30
        else AssetStatus.ACTIVE
    )

    return Asset(
        id=asset_id,
        name=name,
        asset_type=AssetType.AERIAL_DRONE,
        status=status,
        battery=battery,
        telemetry=Telemetry(
            latitude=round(latitude, 6),
            longitude=round(longitude, 6),
            altitude=round(altitude, 1),
            speed=round(speed, 1),
            heading=round(heading, 1),
        ),
    )


def _calculate_heading(
    latitude_speed: float,
    longitude_speed: float,
) -> float:
    heading = math.degrees(
        math.atan2(
            longitude_speed,
            latitude_speed,
        )
    )

    return heading % 360