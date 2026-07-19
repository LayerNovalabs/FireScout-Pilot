import math
import time

from app.models.asset import (
    Asset,
    AssetStatus,
    AssetType,
)
from app.models.mission_plan import MissionPlanStatus
from app.models.telemetry import Telemetry
from app.services.mission_control import (
    ActiveMission,
    get_active_mission,
)
from app.services.mission_execution_engine import (
    MissionExecutionSnapshot,
)
from app.services.mission_runtime import (
    get_mission_execution_snapshots,
)
from app.services.scenario_manager import ScenarioType


_START_TIME = time.monotonic()

MIN_MISSION_BATTERY = 30

_RESCUE_EVENT_PREFIX = "rescue-"


def get_simulated_assets() -> list[Asset]:
    """
    Devuelve los activos del escenario Wildfire.

    Orden de prioridad:

    1. Misión de rescate activa.
    2. Ruta automática de búsqueda.
    3. Misión operativa convencional.
    4. Movimiento base del simulador.
    """

    elapsed = (
        time.monotonic()
        - _START_TIME
    )

    assets = [
        _create_alpha(elapsed),
        _create_bravo(elapsed),
        _create_charlie(elapsed),
    ]

    snapshots = get_mission_execution_snapshots(
        ScenarioType.WILDFIRE
    )

    snapshots_by_asset_id = {
        snapshot.plan.assigned_asset_id: snapshot
        for snapshot in snapshots
    }

    synchronized_assets: list[Asset] = []

    for asset in assets:
        active_mission = get_active_mission(
            asset.id
        )

        snapshot = snapshots_by_asset_id.get(
            asset.id
        )

        if _is_rescue_mission(
            active_mission
        ):
            # Una víctima confirmada interrumpe
            # inmediatamente la ruta de búsqueda.
            asset = _apply_active_mission(
                asset=asset,
                mission=active_mission,
            )

        elif snapshot is not None:
            # El Mission Planner controla el dron
            # durante tránsito y búsqueda.
            asset = _apply_search_execution(
                asset=asset,
                snapshot=snapshot,
            )

        elif active_mission is not None:
            # Compatibilidad con las asignaciones
            # convencionales del Decision Engine.
            asset = _apply_active_mission(
                asset=asset,
                mission=active_mission,
            )

        synchronized_assets.append(
            asset
        )

    return synchronized_assets


def _is_rescue_mission(
    mission: ActiveMission | None,
) -> bool:
    """
    Indica si la misión activa corresponde
    a una respuesta de rescate.
    """

    return (
        mission is not None
        and mission.event_id.startswith(
            _RESCUE_EVENT_PREFIX
        )
    )


def _apply_search_execution(
    asset: Asset,
    snapshot: MissionExecutionSnapshot,
) -> Asset:
    """
    Sincroniza el activo con su plan automático
    de búsqueda.
    """

    if asset.telemetry is None:
        return asset

    asset.telemetry.latitude = (
        snapshot.position.latitude
    )

    asset.telemetry.longitude = (
        snapshot.position.longitude
    )

    asset.telemetry.altitude = round(
        snapshot.altitude_m,
        1,
    )

    asset.telemetry.speed = round(
        snapshot.speed_mps,
        1,
    )

    asset.telemetry.heading = round(
        snapshot.heading_degrees,
        1,
    )

    if (
        snapshot.plan.status
        == MissionPlanStatus.COMPLETED
    ):
        asset.status = AssetStatus.READY
    else:
        asset.status = AssetStatus.ACTIVE

    return asset


def _apply_active_mission(
    asset: Asset,
    mission: ActiveMission,
) -> Asset:
    """
    Mueve el activo desde el punto inicial
    de la misión hasta su objetivo.

    La misión conserva su instante original, por lo que
    el movimiento no se reinicia en cada actualización.
    """

    if asset.telemetry is None:
        return asset

    if (
        asset.battery is None
        or asset.battery < MIN_MISSION_BATTERY
    ):
        return asset

    mission_elapsed = (
        time.monotonic()
        - mission.assigned_at
    )

    distance_km = _calculate_distance_km(
        latitude_1=mission.start_latitude,
        longitude_1=mission.start_longitude,
        latitude_2=mission.target_latitude,
        longitude_2=mission.target_longitude,
    )

    distance_m = (
        distance_km * 1000.0
    )

    if distance_m <= 0:
        progress = 1.0
    else:
        travelled_m = (
            mission_elapsed
            * mission.cruise_speed_mps
        )

        progress = min(
            1.0,
            travelled_m / distance_m,
        )

    latitude = (
        mission.start_latitude
        + (
            mission.target_latitude
            - mission.start_latitude
        )
        * progress
    )

    longitude = (
        mission.start_longitude
        + (
            mission.target_longitude
            - mission.start_longitude
        )
        * progress
    )

    arrived = (
        progress >= 1.0
    )

    if arrived:
        heading = asset.telemetry.heading
        speed = 0.0
        asset.status = AssetStatus.READY
    else:
        heading = _calculate_target_heading(
            current_latitude=latitude,
            current_longitude=longitude,
            target_latitude=(
                mission.target_latitude
            ),
            target_longitude=(
                mission.target_longitude
            ),
        )

        speed = mission.cruise_speed_mps
        asset.status = AssetStatus.ACTIVE

    asset.telemetry.latitude = round(
        latitude,
        6,
    )

    asset.telemetry.longitude = round(
        longitude,
        6,
    )

    asset.telemetry.speed = round(
        speed,
        1,
    )

    asset.telemetry.heading = round(
        heading,
        1,
    )

    return asset


def _create_alpha(
    elapsed: float,
) -> Asset:
    """
    Crea Simulator Alpha.
    """

    angle = elapsed * 0.08

    latitude = (
        41.3885
        + 0.0018
        * math.sin(angle)
    )

    longitude = (
        2.1705
        + 0.0024
        * math.cos(angle)
    )

    latitude_speed = (
        0.0018
        * 0.08
        * math.cos(angle)
    )

    longitude_speed = (
        -0.0024
        * 0.08
        * math.sin(angle)
    )

    return _build_asset(
        asset_id="sim-001",
        name="Simulator Alpha",
        starting_battery=92,
        elapsed=elapsed,
        latitude=latitude,
        longitude=longitude,
        altitude=(
            120.0
            + 4.0
            * math.sin(elapsed / 5.0)
        ),
        speed=(
            14.5
            + 1.2
            * math.sin(elapsed / 3.0)
        ),
        heading=_calculate_heading(
            latitude_speed,
            longitude_speed,
        ),
    )


def _create_bravo(
    elapsed: float,
) -> Asset:
    """
    Crea Simulator Bravo.
    """

    latitude_angle = (
        elapsed * 0.045
    )

    longitude_angle = (
        elapsed * 0.025
    )

    latitude = (
        41.3905
        + 0.0013
        * math.sin(latitude_angle)
    )

    longitude = (
        2.1645
        + 0.0038
        * math.sin(longitude_angle)
    )

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
        altitude=(
            105.0
            + 3.0
            * math.sin(elapsed / 6.0)
        ),
        speed=(
            12.8
            + 1.0
            * math.cos(elapsed / 4.0)
        ),
        heading=_calculate_heading(
            latitude_speed,
            longitude_speed,
        ),
    )


def _create_charlie(
    elapsed: float,
) -> Asset:
    """
    Charlie permanece en la base porque su batería
    está por debajo del mínimo operativo.
    """

    return _build_asset(
        asset_id="sim-003",
        name="Simulator Charlie",
        starting_battery=28,
        elapsed=elapsed,
        latitude=41.3848,
        longitude=2.1670,
        altitude=0.0,
        speed=0.0,
        heading=0.0,
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
    """
    Construye un activo aéreo simulado.
    """

    battery = max(
        0,
        int(
            starting_battery
            - elapsed / 120
        ),
    )

    status = (
        AssetStatus.WARNING
        if battery <= MIN_MISSION_BATTERY
        else AssetStatus.ACTIVE
    )

    return Asset(
        id=asset_id,
        name=name,
        asset_type=AssetType.AERIAL_DRONE,
        status=status,
        battery=battery,
        telemetry=Telemetry(
            latitude=round(
                latitude,
                6,
            ),
            longitude=round(
                longitude,
                6,
            ),
            altitude=round(
                altitude,
                1,
            ),
            speed=round(
                speed,
                1,
            ),
            heading=round(
                heading,
                1,
            ),
        ),
    )


def _calculate_distance_km(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """
    Calcula la distancia geográfica usando Haversine.
    """

    earth_radius_km = 6371.0

    latitude_1_radians = math.radians(
        latitude_1
    )

    latitude_2_radians = math.radians(
        latitude_2
    )

    latitude_delta = math.radians(
        latitude_2 - latitude_1
    )

    longitude_delta = math.radians(
        longitude_2 - longitude_1
    )

    haversine_value = (
        math.sin(
            latitude_delta / 2.0
        ) ** 2
        + math.cos(latitude_1_radians)
        * math.cos(latitude_2_radians)
        * math.sin(
            longitude_delta / 2.0
        ) ** 2
    )

    angular_distance = (
        2.0
        * math.atan2(
            math.sqrt(haversine_value),
            math.sqrt(
                1.0 - haversine_value
            ),
        )
    )

    return (
        earth_radius_km
        * angular_distance
    )


def _calculate_target_heading(
    current_latitude: float,
    current_longitude: float,
    target_latitude: float,
    target_longitude: float,
) -> float:
    """
    Calcula el rumbo desde la posición actual
    hasta el objetivo.
    """

    latitude_1 = math.radians(
        current_latitude
    )

    latitude_2 = math.radians(
        target_latitude
    )

    longitude_delta = math.radians(
        target_longitude
        - current_longitude
    )

    east_component = (
        math.sin(longitude_delta)
        * math.cos(latitude_2)
    )

    north_component = (
        math.cos(latitude_1)
        * math.sin(latitude_2)
        - math.sin(latitude_1)
        * math.cos(latitude_2)
        * math.cos(longitude_delta)
    )

    heading = math.degrees(
        math.atan2(
            east_component,
            north_component,
        )
    )

    return (
        heading + 360.0
    ) % 360.0


def _calculate_heading(
    latitude_speed: float,
    longitude_speed: float,
) -> float:
    """
    Calcula el rumbo a partir de las componentes
    del movimiento.
    """

    heading = math.degrees(
        math.atan2(
            longitude_speed,
            latitude_speed,
        )
    )

    return (
        heading + 360.0
    ) % 360.0