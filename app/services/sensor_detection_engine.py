import math
import time
from dataclasses import dataclass

from app.models.detection import (
    DetectionStatus,
    DetectionTargetType,
    SensorDetection,
    SensorMissionStatus,
    SensorType,
)
from app.models.mission_plan import (
    MissionPlanStatus,
    SearchMissionPlan,
)
from app.models.search_area import GeoPoint
from app.services.mission_execution_engine import (
    MissionExecutionSnapshot,
)
from app.services.mission_runtime import (
    get_mission_execution_snapshots,
)
from app.services.scenario_manager import (
    ScenarioType,
    get_active_scenario,
)


_EARTH_RADIUS_M = 6_371_000.0

_ENGINE_START_TIME = time.monotonic()


@dataclass(frozen=True)
class _HiddenTarget:
    """
    Objetivo interno del simulador.

    Esta información nunca se devuelve directamente
    al Command Center antes de producirse la detección.
    """

    id: str
    related_event_id: str
    position: GeoPoint
    waypoint_index: int


@dataclass
class _DetectionMemory:
    """
    Memoria interna de una detección.

    Permite mantener la detección después de que
    el dron abandone el radio del sensor.
    """

    first_detected_at_seconds: float
    last_updated_at_seconds: float
    hit_count: int
    confidence_percent: float
    status: DetectionStatus


_DETECTION_MEMORY: dict[
    str,
    _DetectionMemory,
] = {}


def reset_sensor_detections() -> None:
    """
    Elimina todas las detecciones almacenadas.
    """

    global _ENGINE_START_TIME

    _DETECTION_MEMORY.clear()
    _ENGINE_START_TIME = time.monotonic()


def get_active_detections() -> list[SensorDetection]:
    """
    Devuelve las detecciones del escenario activo.
    """

    return get_detections(
        get_active_scenario()
    )


def get_detections(
    scenario: ScenarioType,
) -> list[SensorDetection]:
    """
    Ejecuta los sensores de todas las misiones
    del escenario indicado.
    """

    snapshots = get_mission_execution_snapshots(
        scenario
    )

    elapsed_seconds = _elapsed_seconds()

    detections: list[SensorDetection] = []

    for snapshot in snapshots:
        detection = _process_snapshot(
            scenario=scenario,
            snapshot=snapshot,
            elapsed_seconds=elapsed_seconds,
        )

        if detection is not None:
            detections.append(detection)

    return detections


def get_active_sensor_statuses(
) -> list[SensorMissionStatus]:
    """
    Devuelve el estado de los sensores del
    escenario activo.
    """

    return get_sensor_statuses(
        get_active_scenario()
    )


def get_sensor_statuses(
    scenario: ScenarioType,
) -> list[SensorMissionStatus]:
    """
    Devuelve información del sensor aunque todavía
    no exista una detección visible.
    """

    snapshots = get_mission_execution_snapshots(
        scenario
    )

    elapsed_seconds = _elapsed_seconds()

    statuses: list[SensorMissionStatus] = []

    for snapshot in snapshots:
        plan = snapshot.plan

        target = _create_hidden_target(
            plan
        )

        (
            sensor_type,
            base_radius_m,
            environment_factor,
        ) = _sensor_parameters(
            scenario=scenario,
            related_event_id=(
                plan.related_event_id
            ),
        )

        effective_radius_m = (
            base_radius_m
            * environment_factor
        )

        distance_m = _distance_m(
            point_1=snapshot.position,
            point_2=target.position,
        )

        memory = _DETECTION_MEMORY.get(
            plan.id
        )

        sensor_active = (
            plan.status
            == MissionPlanStatus.IN_PROGRESS
        )

        if memory is None:
            detection_status = None

            if sensor_active:
                message = (
                    "Sensor scanning the assigned "
                    "search corridor."
                )
            elif (
                plan.status
                == MissionPlanStatus.PLANNED
            ):
                message = (
                    "Sensor waiting for the drone "
                    "to enter the search area."
                )
            else:
                message = (
                    "Search mission completed without "
                    "an active sensor contact."
                )
        else:
            _update_confirmation_state(
                memory=memory,
                elapsed_seconds=elapsed_seconds,
            )

            detection_status = memory.status

            if (
                memory.status
                == DetectionStatus.CONFIRMED
            ):
                message = (
                    "Confirmed person detection. "
                    "Coordinates available to command."
                )
            else:
                message = (
                    "Possible person detection. "
                    "Sensor confirmation in progress."
                )

        statuses.append(
            SensorMissionStatus(
                mission_plan_id=plan.id,
                scenario=plan.scenario,
                related_event_id=(
                    plan.related_event_id
                ),
                asset_id=plan.assigned_asset_id,
                asset_name=(
                    plan.assigned_asset_name
                ),
                sensor_type=sensor_type,
                sensor_active=sensor_active,
                detection_radius_m=round(
                    effective_radius_m,
                    1,
                ),
                environment_factor=round(
                    environment_factor,
                    2,
                ),
                nearest_target_distance_m=round(
                    distance_m,
                    1,
                ),
                detection_status=(
                    detection_status
                ),
                message=message,
            )
        )

    return statuses


def _process_snapshot(
    scenario: ScenarioType,
    snapshot: MissionExecutionSnapshot,
    elapsed_seconds: float,
) -> SensorDetection | None:
    """
    Procesa una lectura del sensor para una misión.
    """

    plan = snapshot.plan

    target = _create_hidden_target(
        plan
    )

    (
        sensor_type,
        base_radius_m,
        environment_factor,
    ) = _sensor_parameters(
        scenario=scenario,
        related_event_id=(
            plan.related_event_id
        ),
    )

    effective_radius_m = (
        base_radius_m
        * environment_factor
    )

    distance_m = _distance_m(
        point_1=snapshot.position,
        point_2=target.position,
    )

    sensor_active = (
        plan.status
        == MissionPlanStatus.IN_PROGRESS
    )

    target_waypoint_reached = (
        sensor_active
        and plan.current_waypoint_index
        >= target.waypoint_index
    )

    inside_detection_radius = (
        sensor_active
        and distance_m
        <= effective_radius_m
    )

    memory = _DETECTION_MEMORY.get(
        plan.id
    )

    if memory is None:
        if not (
            inside_detection_radius
            or target_waypoint_reached
        ):
            return None

        confidence = _calculate_confidence(
            distance_m=distance_m,
            detection_radius_m=(
                effective_radius_m
            ),
            environment_factor=(
                environment_factor
            ),
            hit_count=1,
        )

        memory = _DetectionMemory(
            first_detected_at_seconds=(
                elapsed_seconds
            ),
            last_updated_at_seconds=(
                elapsed_seconds
            ),
            hit_count=1,
            confidence_percent=confidence,
            status=DetectionStatus.POSSIBLE,
        )

        _DETECTION_MEMORY[plan.id] = memory

    else:
        if inside_detection_radius:
            memory.hit_count += 1

            confidence = _calculate_confidence(
                distance_m=distance_m,
                detection_radius_m=(
                    effective_radius_m
                ),
                environment_factor=(
                    environment_factor
                ),
                hit_count=memory.hit_count,
            )

            memory.confidence_percent = max(
                memory.confidence_percent,
                confidence,
            )

            memory.last_updated_at_seconds = (
                elapsed_seconds
            )

        _update_confirmation_state(
            memory=memory,
            elapsed_seconds=elapsed_seconds,
        )

    return _build_detection(
        plan=plan,
        target=target,
        sensor_type=sensor_type,
        effective_radius_m=(
            effective_radius_m
        ),
        environment_factor=(
            environment_factor
        ),
        distance_m=distance_m,
        memory=memory,
    )


def _update_confirmation_state(
    memory: _DetectionMemory,
    elapsed_seconds: float,
) -> None:
    """
    Convierte una detección posible en confirmada.

    Se confirma mediante:

    - dos lecturas válidas del sensor; o
    - fusión automática después de tres segundos.
    """

    confirmation_elapsed = (
        elapsed_seconds
        - memory.first_detected_at_seconds
    )

    if (
        memory.hit_count >= 2
        or confirmation_elapsed >= 3.0
        or memory.confidence_percent >= 82.0
    ):
        memory.status = (
            DetectionStatus.CONFIRMED
        )

        memory.confidence_percent = max(
            memory.confidence_percent,
            88.0,
        )

        memory.last_updated_at_seconds = (
            elapsed_seconds
        )


def _build_detection(
    plan: SearchMissionPlan,
    target: _HiddenTarget,
    sensor_type: SensorType,
    effective_radius_m: float,
    environment_factor: float,
    distance_m: float,
    memory: _DetectionMemory,
) -> SensorDetection:
    """
    Construye el objeto visible para el operador.
    """

    if (
        memory.status
        == DetectionStatus.CONFIRMED
    ):
        message = (
            f"CONFIRMED PERSON DETECTION by "
            f"{plan.assigned_asset_name}. "
            f"Dispatch rescue resources to "
            f"{target.position.latitude:.6f}, "
            f"{target.position.longitude:.6f}."
        )
    else:
        message = (
            f"POSSIBLE PERSON DETECTION by "
            f"{plan.assigned_asset_name}. "
            "Additional sensor confirmation required."
        )

    return SensorDetection(
        id=(
            "detection-"
            f"{plan.related_event_id}"
        ),
        scenario=plan.scenario,
        related_event_id=(
            plan.related_event_id
        ),
        source_asset_id=(
            plan.assigned_asset_id
        ),
        source_asset_name=(
            plan.assigned_asset_name
        ),
        target_type=(
            DetectionTargetType.PERSON
        ),
        sensor_type=sensor_type,
        status=memory.status,
        latitude=target.position.latitude,
        longitude=target.position.longitude,
        confidence_percent=round(
            memory.confidence_percent,
            1,
        ),
        detection_radius_m=round(
            effective_radius_m,
            1,
        ),
        distance_to_target_m=round(
            distance_m,
            1,
        ),
        environment_factor=round(
            environment_factor,
            2,
        ),
        first_detected_at_seconds=round(
            memory.first_detected_at_seconds,
            1,
        ),
        last_updated_at_seconds=round(
            memory.last_updated_at_seconds,
            1,
        ),
        message=message,
    )


def _create_hidden_target(
    plan: SearchMissionPlan,
) -> _HiddenTarget:
    """
    Coloca la víctima en un waypoint interno
    de la ruta.

    La posición se mantiene privada hasta que
    el sensor produzca una detección.
    """

    if not plan.waypoints:
        return _HiddenTarget(
            id=(
                "hidden-target-"
                f"{plan.related_event_id}"
            ),
            related_event_id=(
                plan.related_event_id
            ),
            position=plan.entry_point,
            waypoint_index=0,
        )

    route_fraction = (
        _target_route_fraction(
            plan.related_event_id
        )
    )

    target_index = round(
        (len(plan.waypoints) - 1)
        * route_fraction
    )

    target_index = max(
        0,
        min(
            target_index,
            len(plan.waypoints) - 1,
        ),
    )

    waypoint = plan.waypoints[
        target_index
    ]

    return _HiddenTarget(
        id=(
            "hidden-target-"
            f"{plan.related_event_id}"
        ),
        related_event_id=(
            plan.related_event_id
        ),
        position=GeoPoint(
            latitude=waypoint.latitude,
            longitude=waypoint.longitude,
        ),
        waypoint_index=target_index,
    )


def _target_route_fraction(
    related_event_id: str,
) -> float:
    """
    Posición aproximada de la víctima dentro
    del recorrido de búsqueda.
    """

    route_fractions = {
        "event-001": 0.42,
        "event-002": 0.63,
        "sar-event-001": 0.55,
    }

    return route_fractions.get(
        related_event_id,
        0.50,
    )


def _sensor_parameters(
    scenario: ScenarioType,
    related_event_id: str,
) -> tuple[
    SensorType,
    float,
    float,
]:
    """
    Devuelve:

    - tipo de sensor;
    - radio base;
    - factor ambiental.

    El humo y las condiciones marítimas reducen
    el alcance útil del sensor.
    """

    if scenario == ScenarioType.MARITIME_SAR:
        return (
            SensorType.MULTISPECTRAL_CAMERA,
            500.0,
            0.84,
        )

    wildfire_environment_factors = {
        "event-001": 0.76,
        "event-002": 0.69,
    }

    environment_factor = (
        wildfire_environment_factors.get(
            related_event_id,
            0.72,
        )
    )

    return (
        SensorType.THERMAL_CAMERA,
        450.0,
        environment_factor,
    )


def _calculate_confidence(
    distance_m: float,
    detection_radius_m: float,
    environment_factor: float,
    hit_count: int,
) -> float:
    """
    Calcula la confianza usando proximidad,
    calidad ambiental y lecturas repetidas.
    """

    if detection_radius_m <= 0:
        return 0.0

    normalized_distance = min(
        1.0,
        distance_m / detection_radius_m,
    )

    proximity_factor = (
        1.0 - normalized_distance
    )

    confidence = (
        48.0
        + proximity_factor * 35.0
        + environment_factor * 10.0
        + max(0, hit_count - 1) * 6.0
    )

    return round(
        min(99.0, confidence),
        1,
    )


def _distance_m(
    point_1: GeoPoint,
    point_2: GeoPoint,
) -> float:
    """
    Distancia geográfica mediante Haversine.
    """

    latitude_1 = math.radians(
        point_1.latitude
    )

    latitude_2 = math.radians(
        point_2.latitude
    )

    latitude_delta = math.radians(
        point_2.latitude
        - point_1.latitude
    )

    longitude_delta = math.radians(
        point_2.longitude
        - point_1.longitude
    )

    haversine_value = (
        math.sin(
            latitude_delta / 2.0
        ) ** 2
        + math.cos(latitude_1)
        * math.cos(latitude_2)
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
        _EARTH_RADIUS_M
        * angular_distance
    )


def _elapsed_seconds() -> float:
    return max(
        0.0,
        time.monotonic()
        - _ENGINE_START_TIME,
    )