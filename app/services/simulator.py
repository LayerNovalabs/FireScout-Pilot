import math
import time

from app.models.asset import Asset, AssetStatus, AssetType
from app.models.telemetry import Telemetry


_START_TIME = time.monotonic()


def get_simulated_assets() -> list[Asset]:
    elapsed = time.monotonic() - _START_TIME

    return [
        _create_drone(
            asset_id="sim-001",
            name="Simulator Alpha",
            starting_battery=92,
            base_altitude=120.0,
            base_speed=14.5,
            phase_degrees=0.0,
            elapsed=elapsed,
        ),
        _create_drone(
            asset_id="sim-002",
            name="Simulator Bravo",
            starting_battery=84,
            base_altitude=105.0,
            base_speed=12.8,
            phase_degrees=120.0,
            elapsed=elapsed,
        ),
        _create_drone(
            asset_id="sim-003",
            name="Simulator Charlie",
            starting_battery=28,
            base_altitude=95.0,
            base_speed=10.2,
            phase_degrees=240.0,
            elapsed=elapsed,
        ),
    ]


def _create_drone(
    asset_id: str,
    name: str,
    starting_battery: int,
    base_altitude: float,
    base_speed: float,
    phase_degrees: float,
    elapsed: float,
) -> Asset:
    angle_degrees = (elapsed * 4.0 + phase_degrees) % 360
    angle_radians = math.radians(angle_degrees)

    latitude = 41.3874 + 0.003 * math.sin(angle_radians)
    longitude = 2.1686 + 0.003 * math.cos(angle_radians)

    altitude = base_altitude + 5.0 * math.sin(
        elapsed / 4.0 + math.radians(phase_degrees)
    )

    speed = base_speed + 1.5 * math.sin(
        elapsed / 3.0 + math.radians(phase_degrees)
    )

    battery = max(0, int(starting_battery - elapsed / 120))

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
            heading=round(angle_degrees, 1),
        ),
    )