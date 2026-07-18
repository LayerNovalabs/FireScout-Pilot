import time

from app.models.mission_plan import SearchMissionPlan
from app.models.search_area import GeoPoint
from app.services.mission_execution_engine import (
    MissionExecutionEngine,
    MissionExecutionSnapshot,
)
from app.services.mission_planner import MissionPlanner
from app.services.scenario_manager import (
    ScenarioType,
    get_active_scenario,
)


# Instante de inicio de cada escenario.
_MISSION_START_TIMES: dict[ScenarioType, float] = {}


# Posiciones iniciales reales de los drones simulados.
_ASSET_LAUNCH_POSITIONS: dict[str, GeoPoint] = {
    "sim-001": GeoPoint(
        latitude=41.3885,
        longitude=2.1705,
    ),
    "sim-002": GeoPoint(
        latitude=41.3905,
        longitude=2.1645,
    ),
    "sar-drone-001": GeoPoint(
        latitude=41.3600,
        longitude=2.2250,
    ),
}


def reset_mission_execution(
    scenario: ScenarioType | None = None,
) -> None:
    """
    Reinicia el progreso de una misión.

    Si no se especifica escenario, reinicia todos
    los relojes de ejecución.
    """

    if scenario is None:
        _MISSION_START_TIMES.clear()
        return

    _MISSION_START_TIMES[scenario] = time.monotonic()


def get_mission_execution_snapshots(
    scenario: ScenarioType,
) -> list[MissionExecutionSnapshot]:
    """
    Devuelve el estado dinámico de todos los planes.

    Cada plan utiliza la posición inicial del dron
    que tiene asignado.
    """

    start_time = _MISSION_START_TIMES.get(
        scenario
    )

    if start_time is None:
        start_time = time.monotonic()

        _MISSION_START_TIMES[scenario] = start_time

    elapsed_seconds = (
        time.monotonic()
        - start_time
    )

    plans = MissionPlanner().get_mission_plans(
        scenario
    )

    execution_engine = MissionExecutionEngine()

    snapshots: list[
        MissionExecutionSnapshot
    ] = []

    for plan in plans:
        (
            launch_position,
            transit_speed_mps,
            search_speed_mps,
            time_scale,
        ) = _execution_parameters(
            scenario=scenario,
            plan=plan,
        )

        snapshot = execution_engine.calculate_snapshot(
            plan=plan,
            launch_position=launch_position,
            elapsed_seconds=elapsed_seconds,
            transit_speed_mps=transit_speed_mps,
            search_speed_mps=search_speed_mps,
            time_scale=time_scale,
        )

        snapshots.append(snapshot)

    return snapshots


def get_executed_mission_plans(
    scenario: ScenarioType,
) -> list[SearchMissionPlan]:
    """
    Devuelve los planes con progreso dinámico.
    """

    return [
        snapshot.plan
        for snapshot
        in get_mission_execution_snapshots(
            scenario
        )
    ]


def get_active_executed_mission_plans(
) -> list[SearchMissionPlan]:
    """
    Devuelve los planes dinámicos del escenario activo.
    """

    return get_executed_mission_plans(
        get_active_scenario()
    )


def get_primary_execution_snapshot(
    scenario: ScenarioType,
) -> MissionExecutionSnapshot | None:
    """
    Devuelve el primer plan del escenario.

    Se conserva para Maritime SAR, donde actualmente
    solo existe una misión aérea.
    """

    snapshots = get_mission_execution_snapshots(
        scenario
    )

    if not snapshots:
        return None

    return snapshots[0]


def get_execution_snapshot_for_asset(
    scenario: ScenarioType,
    asset_id: str,
) -> MissionExecutionSnapshot | None:
    """
    Devuelve únicamente el estado de ejecución
    correspondiente al dron indicado.
    """

    snapshots = get_mission_execution_snapshots(
        scenario
    )

    for snapshot in snapshots:
        if (
            snapshot.plan.assigned_asset_id
            == asset_id
        ):
            return snapshot

    return None


def _execution_parameters(
    scenario: ScenarioType,
    plan: SearchMissionPlan,
) -> tuple[
    GeoPoint,
    float,
    float,
    float,
]:
    """
    Devuelve:

    - posición inicial del activo asignado;
    - velocidad de tránsito;
    - velocidad de búsqueda;
    - escala temporal.
    """

    launch_position = _ASSET_LAUNCH_POSITIONS.get(
        plan.assigned_asset_id
    )

    if launch_position is None:
        launch_position = plan.entry_point

    if scenario == ScenarioType.MARITIME_SAR:
        return (
            launch_position,
            16.0,
            14.0,
            8.0,
        )

    return (
        launch_position,
        14.0,
        12.0,
        7.0,
    )