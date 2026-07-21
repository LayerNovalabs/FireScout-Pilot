import math
import time

from app.models.asset import (
    Asset,
    AssetStatus,
    AssetType,
)
from app.models.detection import (
    DetectionStatus,
    SensorDetection,
)
from app.models.mission_plan import MissionPlanStatus
from app.models.telemetry import Telemetry
from app.services.mission_execution_engine import (
    MissionExecutionSnapshot,
)
from app.services.mission_runtime import (
    get_primary_execution_snapshot,
)
from app.services.scenario_manager import ScenarioType
from app.services.search_area_engine import SearchAreaEngine
from app.services.sensor_detection_engine import (
    get_detections,
)


SIMULATION_TIME_SCALE = 8.0

_DRONE_START_LATITUDE = 41.3600
_DRONE_START_LONGITUDE = 2.2250

_BOAT_START_LATITUDE = 41.3510
_BOAT_START_LONGITUDE = 2.2150

_BOAT_SPEED_MPS = 8.0

_MISSION_START_TIME: float | None = None

_RESCUE_START_TIME: float | None = None
_RESCUE_START_LATITUDE: float | None = None
_RESCUE_START_LONGITUDE: float | None = None


def reset_maritime_simulation() -> None:
    """
    Reinicia completamente la simulación marítima.

    También elimina la ruta de rescate anterior para
    que el barco vuelva a comenzar desde su posición
    inicial.
    """

    global _MISSION_START_TIME
    global _RESCUE_START_TIME
    global _RESCUE_START_LATITUDE
    global _RESCUE_START_LONGITUDE

    _MISSION_START_TIME = time.monotonic()

    _RESCUE_START_TIME = None
    _RESCUE_START_LATITUDE = None
    _RESCUE_START_LONGITUDE = None


def get_maritime_assets() -> list[Asset]:
    """
    Devuelve los activos del escenario Maritime SAR.

    El dron utiliza el estado del Mission Planner.

    El barco:

    - se dirige primero al centro de búsqueda;
    - espera mientras no exista una víctima confirmada;
    - cuando el sensor confirma a la persona, cambia
      inmediatamente su destino;
    - navega hacia las coordenadas exactas de la víctima.
    """

    global _MISSION_START_TIME

    if _MISSION_START_TIME is None:
        reset_maritime_simulation()

    if _MISSION_START_TIME is None:
        return []

    current_time = time.monotonic()

    real_elapsed_seconds = (
        current_time
        - _MISSION_START_TIME
    )

    simulated_elapsed_seconds = (
        real_elapsed_seconds
        * SIMULATION_TIME_SCALE
    )

    search_areas = (
        SearchAreaEngine().get_search_areas(
            ScenarioType.MARITIME_SAR
        )
    )

    if not search_areas:
        return []

    target_area = search_areas[0]

    staging_latitude = (
        target_area.estimated_center.latitude
    )

    staging_longitude = (
        target_area.estimated_center.longitude
    )

    execution_snapshot = (
        get_primary_execution_snapshot(
            ScenarioType.MARITIME_SAR
        )
    )

    confirmed_detection = (
        _get_confirmed_maritime_detection()
    )

    drone = _create_sar_drone(
        snapshot=execution_snapshot,
        real_elapsed_seconds=real_elapsed_seconds,
    )

    boat = _create_rescue_boat(
        staging_elapsed_seconds=(
            simulated_elapsed_seconds
        ),
        real_elapsed_seconds=(
            real_elapsed_seconds
        ),
        current_time=current_time,
        staging_latitude=staging_latitude,
        staging_longitude=staging_longitude,
        detection=confirmed_detection,
    )

    return [
        drone,
        boat,
    ]


def _get_confirmed_maritime_detection(
) -> SensorDetection | None:
    """
    Obtiene la primera detección confirmada de
    una persona en el escenario Maritime SAR.
    """

    detections = get_detections(
        ScenarioType.MARITIME_SAR
    )

    for detection in detections:
        if (
            detection.status
            == DetectionStatus.CONFIRMED
        ):
            return detection

    return None


def _create_sar_drone(
    snapshot: MissionExecutionSnapshot | None,
    real_elapsed_seconds: float,
) -> Asset:
    """
    Crea el dron SAR utilizando el estado dinámico
    del Mission Execution Engine.
    """

    if snapshot is None:
        return Asset(
            id="sar-drone-001",
            name="SAR Drone One",
            asset_type=AssetType.AERIAL_DRONE,
            status=AssetStatus.READY,
            battery=94,
            telemetry=Telemetry(
                latitude=_DRONE_START_LATITUDE,
                longitude=_DRONE_START_LONGITUDE,
                altitude=0.0,
                speed=0.0,
                heading=0.0,
            ),
        )

    if (
        snapshot.plan.status
        == MissionPlanStatus.COMPLETED
    ):
        status = AssetStatus.READY
    else:
        status = AssetStatus.ACTIVE

    battery = max(
        0,
        int(
            94
            - real_elapsed_seconds / 180
        ),
    )

    return Asset(
        id="sar-drone-001",
        name="SAR Drone One",
        asset_type=AssetType.AERIAL_DRONE,
        status=status,
        battery=battery,
        telemetry=Telemetry(
            latitude=snapshot.position.latitude,
            longitude=snapshot.position.longitude,
            altitude=round(
                snapshot.altitude_m,
                1,
            ),
            speed=round(
                snapshot.speed_mps,
                1,
            ),
            heading=round(
                snapshot.heading_degrees,
                1,
            ),
        ),
    )


def _create_rescue_boat(
    staging_elapsed_seconds: float,
    real_elapsed_seconds: float,
    current_time: float,
    staging_latitude: float,
    staging_longitude: float,
    detection: SensorDetection | None,
) -> Asset:
    """
    Crea la embarcación de rescate.

    Antes de la detección se dirige al centro de
    búsqueda. Después de la confirmación navega
    hacia las coordenadas exactas de la víctima.
    """

    global _RESCUE_START_TIME
    global _RESCUE_START_LATITUDE
    global _RESCUE_START_LONGITUDE

    if detection is not None:
        if (
            _RESCUE_START_TIME is None
            or _RESCUE_START_LATITUDE is None
            or _RESCUE_START_LONGITUDE is None
        ):
            (
                current_latitude,
                current_longitude,
                _,
                _,
            ) = _move_towards_target(
                start_latitude=(
                    _BOAT_START_LATITUDE
                ),
                start_longitude=(
                    _BOAT_START_LONGITUDE
                ),
                target_latitude=(
                    staging_latitude
                ),
                target_longitude=(
                    staging_longitude
                ),
                speed_mps=_BOAT_SPEED_MPS,
                elapsed_seconds=(
                    staging_elapsed_seconds
                ),
                arrival_radius_meters=15.0,
            )

            _RESCUE_START_TIME = current_time
            _RESCUE_START_LATITUDE = (
                current_latitude
            )
            _RESCUE_START_LONGITUDE = (
                current_longitude
            )

        rescue_elapsed_seconds = (
            current_time
            - _RESCUE_START_TIME
        )

        simulated_rescue_elapsed = (
            rescue_elapsed_seconds
            * SIMULATION_TIME_SCALE
        )

        (
            latitude,
            longitude,
            heading,
            arrived,
        ) = _move_towards_target(
            start_latitude=(
                _RESCUE_START_LATITUDE
            ),
            start_longitude=(
                _RESCUE_START_LONGITUDE
            ),
            target_latitude=(
                detection.latitude
            ),
            target_longitude=(
                detection.longitude
            ),
            speed_mps=_BOAT_SPEED_MPS,
            elapsed_seconds=(
                simulated_rescue_elapsed
            ),
            arrival_radius_meters=20.0,
        )

    else:
        (
            latitude,
            longitude,
            heading,
            arrived,
        ) = _move_towards_target(
            start_latitude=(
                _BOAT_START_LATITUDE
            ),
            start_longitude=(
                _BOAT_START_LONGITUDE
            ),
            target_latitude=(
                staging_latitude
            ),
            target_longitude=(
                staging_longitude
            ),
            speed_mps=_BOAT_SPEED_MPS,
            elapsed_seconds=(
                staging_elapsed_seconds
            ),
            arrival_radius_meters=15.0,
        )

    return Asset(
        id="rescue-boat-001",
        name="Rescue Boat One",
        asset_type=(
            AssetType.MARITIME_VEHICLE
        ),
        status=(
            AssetStatus.READY
            if arrived
            else AssetStatus.ACTIVE
        ),
        battery=max(
            0,
            int(
                88
                - real_elapsed_seconds / 300
            ),
        ),
        telemetry=Telemetry(
            latitude=latitude,
            longitude=longitude,
            altitude=0.0,
            speed=(
                0.0
                if arrived
                else _BOAT_SPEED_MPS
            ),
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
) -> tuple[
    float,
    float,
    float,
    bool,
]:
    """
    Calcula la posición de un activo que se desplaza
    en línea recta hacia un objetivo.
    """

    total_distance_meters = (
        _calculate_distance_meters(
            latitude_1=start_latitude,
            longitude_1=start_longitude,
            latitude_2=target_latitude,
            longitude_2=target_longitude,
        )
    )

    heading = _calculate_heading(
        latitude_1=start_latitude,
        longitude_1=start_longitude,
        latitude_2=target_latitude,
        longitude_2=target_longitude,
    )

    if (
        total_distance_meters
        <= arrival_radius_meters
    ):
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

    progress = (
        travelled_meters
        / total_distance_meters
    )

    latitude = (
        start_latitude
        + (
            target_latitude
            - start_latitude
        )
        * progress
    )

    longitude = (
        start_longitude
        + (
            target_longitude
            - start_longitude
        )
        * progress
    )

    remaining_distance_meters = (
        total_distance_meters
        - travelled_meters
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
    """
    Calcula la distancia entre dos coordenadas
    mediante la fórmula de Haversine.
    """

    earth_radius_meters = 6_371_000.0

    latitude_1_radians = math.radians(
        latitude_1
    )

    latitude_2_radians = math.radians(
        latitude_2
    )

    latitude_delta = math.radians(
        latitude_2
        - latitude_1
    )

    longitude_delta = math.radians(
        longitude_2
        - longitude_1
    )

    haversine_value = (
        math.sin(
            latitude_delta / 2
        ) ** 2
        + math.cos(latitude_1_radians)
        * math.cos(latitude_2_radians)
        * math.sin(
            longitude_delta / 2
        ) ** 2
    )

    angular_distance = (
        2
        * math.atan2(
            math.sqrt(haversine_value),
            math.sqrt(
                1 - haversine_value
            ),
        )
    )

    return (
        earth_radius_meters
        * angular_distance
    )


def _calculate_heading(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """
    Calcula el rumbo desde una posición
    hasta otra.
    """

    latitude_1_radians = math.radians(
        latitude_1
    )

    latitude_2_radians = math.radians(
        latitude_2
    )

    longitude_delta = math.radians(
        longitude_2
        - longitude_1
    )

    east_component = (
        math.sin(longitude_delta)
        * math.cos(latitude_2_radians)
    )

    north_component = (
        math.cos(latitude_1_radians)
        * math.sin(latitude_2_radians)
        - math.sin(latitude_1_radians)
        * math.cos(latitude_2_radians)
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