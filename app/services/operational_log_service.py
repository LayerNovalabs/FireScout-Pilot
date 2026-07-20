import time
from datetime import datetime, timezone
from threading import RLock

from app.models.operational_log import (
    OperationalLogEntry,
    OperationalLogSeverity,
    OperationalLogType,
    OperationalTimeline,
)
from app.services.decision_engine import (
    get_operational_recommendations,
)
from app.services.maritime_decision_engine import (
    get_maritime_recommendations,
)
from app.services.mission_runtime import (
    get_active_executed_mission_plans,
)
from app.services.scenario_manager import (
    ScenarioType,
    get_active_scenario,
)
from app.services.sensor_detection_engine import (
    get_active_detections,
    get_active_sensor_statuses,
)


_MAX_LOG_ENTRIES = 500

_LOG_LOCK = RLock()

_LOG_START_TIMES: dict[str, float] = {}

_LOG_ENTRIES: dict[
    str,
    list[OperationalLogEntry],
] = {}

_OBSERVED_STATES: dict[
    str,
    dict[str, object],
] = {}

_NEXT_ENTRY_NUMBER = 1


def get_active_operational_timeline(
) -> OperationalTimeline:
    """
    Actualiza y devuelve la cronología del
    escenario activo.

    El servicio observa:

    - planes de búsqueda;
    - activación de sensores;
    - detecciones;
    - asignaciones;
    - misiones de rescate.
    """

    scenario = get_active_scenario()
    scenario_key = scenario.value

    with _LOG_LOCK:
        _initialize_scenario(
            scenario
        )

        _observe_missions(
            scenario_key
        )

        _observe_sensors(
            scenario_key
        )

        _observe_detections(
            scenario_key
        )

        _observe_recommendations(
            scenario=scenario,
            scenario_key=scenario_key,
        )

        entries = list(
            _LOG_ENTRIES.get(
                scenario_key,
                [],
            )
        )

        return OperationalTimeline(
            scenario=scenario_key,
            generated_at_iso=_utc_now_iso(),
            total_entries=len(entries),
            entries=entries,
        )


def reset_operational_log(
    scenario: ScenarioType | None = None,
) -> None:
    """
    Reinicia el historial operativo.

    Si no se indica escenario, se eliminan todos
    los historiales almacenados.
    """

    with _LOG_LOCK:
        if scenario is None:
            _LOG_START_TIMES.clear()
            _LOG_ENTRIES.clear()
            _OBSERVED_STATES.clear()
            return

        scenario_key = scenario.value

        _LOG_START_TIMES.pop(
            scenario_key,
            None,
        )

        _LOG_ENTRIES.pop(
            scenario_key,
            None,
        )

        _OBSERVED_STATES.pop(
            scenario_key,
            None,
        )


def record_scenario_change(
    scenario: ScenarioType,
) -> None:
    """
    Reinicia el historial del escenario seleccionado
    y registra su activación.
    """

    with _LOG_LOCK:
        reset_operational_log(
            scenario
        )

        _initialize_scenario(
            scenario
        )

        _append_entry(
            scenario_key=scenario.value,
            entry_type=(
                OperationalLogType.SCENARIO
            ),
            severity=(
                OperationalLogSeverity.SUCCESS
            ),
            title="Scenario activated",
            message=(
                f"{_scenario_label(scenario)} "
                "simulation activated successfully."
            ),
        )


def _initialize_scenario(
    scenario: ScenarioType,
) -> None:
    """
    Inicializa las estructuras internas necesarias
    para registrar un escenario.
    """

    scenario_key = scenario.value

    if scenario_key in _LOG_START_TIMES:
        return

    _LOG_START_TIMES[scenario_key] = (
        time.monotonic()
    )

    _LOG_ENTRIES[scenario_key] = []

    _OBSERVED_STATES[scenario_key] = {}

    _append_entry(
        scenario_key=scenario_key,
        entry_type=OperationalLogType.SYSTEM,
        severity=OperationalLogSeverity.INFO,
        title="Operational timeline started",
        message=(
            f"FireScout started recording the "
            f"{_scenario_label(scenario)} "
            "operational timeline."
        ),
    )


def _observe_missions(
    scenario_key: str,
) -> None:
    """
    Registra los cambios de estado de los planes
    automáticos de búsqueda.
    """

    plans = (
        get_active_executed_mission_plans()
    )

    observed = _OBSERVED_STATES[
        scenario_key
    ]

    for plan in plans:
        status = _enum_value(
            plan.status
        )

        state_key = (
            f"mission:{plan.id}"
        )

        previous_status = observed.get(
            state_key
        )

        if previous_status == status:
            continue

        observed[state_key] = status

        if status == "planned":
            _append_entry(
                scenario_key=scenario_key,
                entry_type=(
                    OperationalLogType.MISSION
                ),
                severity=(
                    OperationalLogSeverity.INFO
                ),
                title="Search mission planned",
                message=(
                    f"{plan.assigned_asset_name} "
                    f"was assigned to "
                    f"{plan.related_event_id}. "
                    f"The mission contains "
                    f"{plan.waypoint_count} waypoints."
                ),
                related_event_id=(
                    plan.related_event_id
                ),
                asset_id=(
                    plan.assigned_asset_id
                ),
                asset_name=(
                    plan.assigned_asset_name
                ),
                mission_status=status,
                latitude=(
                    plan.entry_point.latitude
                ),
                longitude=(
                    plan.entry_point.longitude
                ),
            )

        elif status == "in_progress":
            _append_entry(
                scenario_key=scenario_key,
                entry_type=(
                    OperationalLogType.MISSION
                ),
                severity=(
                    OperationalLogSeverity.SUCCESS
                ),
                title="Search started",
                message=(
                    f"{plan.assigned_asset_name} "
                    "entered the assigned search area "
                    f"for {plan.related_event_id}."
                ),
                related_event_id=(
                    plan.related_event_id
                ),
                asset_id=(
                    plan.assigned_asset_id
                ),
                asset_name=(
                    plan.assigned_asset_name
                ),
                mission_status=status,
            )

        elif status == "completed":
            _append_entry(
                scenario_key=scenario_key,
                entry_type=(
                    OperationalLogType.MISSION
                ),
                severity=(
                    OperationalLogSeverity.SUCCESS
                ),
                title="Search completed",
                message=(
                    f"{plan.assigned_asset_name} "
                    f"completed 100% of the search "
                    f"route for {plan.related_event_id}."
                ),
                related_event_id=(
                    plan.related_event_id
                ),
                asset_id=(
                    plan.assigned_asset_id
                ),
                asset_name=(
                    plan.assigned_asset_name
                ),
                mission_status=status,
            )


def _observe_sensors(
    scenario_key: str,
) -> None:
    """
    Registra cuándo se activa o se desactiva
    cada sensor.
    """

    statuses = (
        get_active_sensor_statuses()
    )

    observed = _OBSERVED_STATES[
        scenario_key
    ]

    for status in statuses:
        state_key = (
            "sensor:"
            f"{status.mission_plan_id}"
        )

        current_state = (
            status.sensor_active
        )

        previous_state = observed.get(
            state_key
        )

        observed[state_key] = (
            current_state
        )

        # No registramos el estado inicial de espera.
        if (
            previous_state is None
            and not current_state
        ):
            continue

        if previous_state == current_state:
            continue

        sensor_name = _enum_value(
            status.sensor_type
        ).replace(
            "_",
            " ",
        )

        if current_state:
            _append_entry(
                scenario_key=scenario_key,
                entry_type=(
                    OperationalLogType.SENSOR
                ),
                severity=(
                    OperationalLogSeverity.INFO
                ),
                title="Sensor activated",
                message=(
                    f"{status.asset_name} activated "
                    f"its {sensor_name}. "
                    f"Effective detection radius: "
                    f"{status.detection_radius_m:.1f} m."
                ),
                related_event_id=(
                    status.related_event_id
                ),
                asset_id=status.asset_id,
                asset_name=status.asset_name,
                mission_status="scanning",
            )

        else:
            _append_entry(
                scenario_key=scenario_key,
                entry_type=(
                    OperationalLogType.SENSOR
                ),
                severity=(
                    OperationalLogSeverity.INFO
                ),
                title="Sensor scan stopped",
                message=(
                    f"{status.asset_name} stopped "
                    f"active scanning for "
                    f"{status.related_event_id}."
                ),
                related_event_id=(
                    status.related_event_id
                ),
                asset_id=status.asset_id,
                asset_name=status.asset_name,
                mission_status="inactive",
            )


def _observe_detections(
    scenario_key: str,
) -> None:
    """
    Registra detecciones posibles y confirmadas.
    """

    detections = get_active_detections()

    observed = _OBSERVED_STATES[
        scenario_key
    ]

    for detection in detections:
        detection_status = _enum_value(
            detection.status
        )

        state_key = (
            f"detection:{detection.id}"
        )

        previous_status = observed.get(
            state_key
        )

        if previous_status == detection_status:
            continue

        observed[state_key] = (
            detection_status
        )

        sensor_name = _enum_value(
            detection.sensor_type
        ).replace(
            "_",
            " ",
        )

        if detection_status == "possible":
            _append_entry(
                scenario_key=scenario_key,
                entry_type=(
                    OperationalLogType.DETECTION
                ),
                severity=(
                    OperationalLogSeverity.WARNING
                ),
                title="Possible person detection",
                message=(
                    f"{detection.source_asset_name} "
                    f"reported a possible person using "
                    f"its {sensor_name}. "
                    f"Confidence: "
                    f"{detection.confidence_percent:.1f}%."
                ),
                related_event_id=(
                    detection.related_event_id
                ),
                asset_id=(
                    detection.source_asset_id
                ),
                asset_name=(
                    detection.source_asset_name
                ),
                mission_status="possible",
                latitude=detection.latitude,
                longitude=detection.longitude,
            )

        elif detection_status == "confirmed":
            _append_entry(
                scenario_key=scenario_key,
                entry_type=(
                    OperationalLogType.DETECTION
                ),
                severity=(
                    OperationalLogSeverity.CRITICAL
                ),
                title="Person detection confirmed",
                message=(
                    f"{detection.source_asset_name} "
                    "confirmed a person at "
                    f"{detection.latitude:.6f}, "
                    f"{detection.longitude:.6f}. "
                    f"Confidence: "
                    f"{detection.confidence_percent:.1f}%."
                ),
                related_event_id=(
                    detection.related_event_id
                ),
                asset_id=(
                    detection.source_asset_id
                ),
                asset_name=(
                    detection.source_asset_name
                ),
                mission_status="confirmed",
                latitude=detection.latitude,
                longitude=detection.longitude,
            )


def _observe_recommendations(
    scenario: ScenarioType,
    scenario_key: str,
) -> None:
    """
    Registra asignaciones, respuestas y rescates
    generados por el Decision Engine.
    """

    if scenario == ScenarioType.MARITIME_SAR:
        recommendations = (
            get_maritime_recommendations()
        )
    else:
        recommendations = (
            get_operational_recommendations()
        )

    observed = _OBSERVED_STATES[
        scenario_key
    ]

    for recommendation in recommendations:
        status = _enum_value(
            recommendation.mission_status
        )

        asset_name = (
            recommendation.assigned_asset_name
        )

        current_state = (
            status,
            asset_name,
        )

        state_key = (
            "recommendation:"
            f"{recommendation.id}"
        )

        previous_state = observed.get(
            state_key
        )

        if previous_state == current_state:
            continue

        observed[state_key] = (
            current_state
        )

        is_rescue = (
            recommendation.id.startswith(
                "recommendation-rescue-"
            )
            or status
            in {
                "victim_located",
                "rescue_completed",
            }
        )

        if status == "pending":
            _append_entry(
                scenario_key=scenario_key,
                entry_type=(
                    OperationalLogType.ASSIGNMENT
                ),
                severity=(
                    OperationalLogSeverity.WARNING
                ),
                title="Resource unavailable",
                message=(
                    recommendation.action
                ),
                related_event_id=(
                    recommendation.related_event_id
                ),
                asset_name=asset_name,
                mission_status=status,
            )

        elif status == "victim_located":
            _append_entry(
                scenario_key=scenario_key,
                entry_type=(
                    OperationalLogType.RESCUE
                ),
                severity=(
                    OperationalLogSeverity.CRITICAL
                ),
                title="Rescue response activated",
                message=(
                    recommendation.action
                ),
                related_event_id=(
                    recommendation.related_event_id
                ),
                asset_name=asset_name,
                mission_status=status,
            )

        elif (
            status == "en_route"
            and is_rescue
        ):
            _append_entry(
                scenario_key=scenario_key,
                entry_type=(
                    OperationalLogType.RESCUE
                ),
                severity=(
                    OperationalLogSeverity.WARNING
                ),
                title="Rescue resource en route",
                message=(
                    recommendation.action
                ),
                related_event_id=(
                    recommendation.related_event_id
                ),
                asset_name=asset_name,
                mission_status=status,
            )

        elif status == "rescue_completed":
            _append_entry(
                scenario_key=scenario_key,
                entry_type=(
                    OperationalLogType.RESCUE
                ),
                severity=(
                    OperationalLogSeverity.SUCCESS
                ),
                title="Rescue completed",
                message=(
                    recommendation.action
                ),
                related_event_id=(
                    recommendation.related_event_id
                ),
                asset_name=asset_name,
                mission_status=status,
            )

        elif status == "at_target":
            _append_entry(
                scenario_key=scenario_key,
                entry_type=(
                    OperationalLogType.ASSIGNMENT
                ),
                severity=(
                    OperationalLogSeverity.SUCCESS
                ),
                title="Resource arrived",
                message=(
                    recommendation.action
                ),
                related_event_id=(
                    recommendation.related_event_id
                ),
                asset_name=asset_name,
                mission_status=status,
            )

        elif status == "searching":
            _append_entry(
                scenario_key=scenario_key,
                entry_type=(
                    OperationalLogType.MISSION
                ),
                severity=(
                    OperationalLogSeverity.INFO
                ),
                title="Search operation active",
                message=(
                    recommendation.action
                ),
                related_event_id=(
                    recommendation.related_event_id
                ),
                asset_name=asset_name,
                mission_status=status,
            )

        elif status == "en_route":
            _append_entry(
                scenario_key=scenario_key,
                entry_type=(
                    OperationalLogType.ASSIGNMENT
                ),
                severity=(
                    OperationalLogSeverity.INFO
                ),
                title="Resource assigned",
                message=(
                    recommendation.action
                ),
                related_event_id=(
                    recommendation.related_event_id
                ),
                asset_name=asset_name,
                mission_status=status,
            )


def _append_entry(
    scenario_key: str,
    entry_type: OperationalLogType,
    severity: OperationalLogSeverity,
    title: str,
    message: str,
    related_event_id: str | None = None,
    asset_id: str | None = None,
    asset_name: str | None = None,
    mission_status: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> None:
    """
    Añade una entrada al historial interno.
    """

    global _NEXT_ENTRY_NUMBER

    entries = _LOG_ENTRIES.setdefault(
        scenario_key,
        [],
    )

    entry = OperationalLogEntry(
        id=(
            "operational-log-"
            f"{_NEXT_ENTRY_NUMBER:06d}"
        ),
        scenario=scenario_key,
        entry_type=entry_type,
        severity=severity,
        title=title,
        message=message,
        related_event_id=related_event_id,
        asset_id=asset_id,
        asset_name=asset_name,
        mission_status=mission_status,
        latitude=latitude,
        longitude=longitude,
        timestamp_seconds=round(
            _elapsed_seconds(
                scenario_key
            ),
            1,
        ),
        timestamp_iso=_utc_now_iso(),
    )

    _NEXT_ENTRY_NUMBER += 1

    entries.append(entry)

    if len(entries) > _MAX_LOG_ENTRIES:
        del entries[
            0:
            len(entries)
            - _MAX_LOG_ENTRIES
        ]


def _elapsed_seconds(
    scenario_key: str,
) -> float:
    start_time = _LOG_START_TIMES.get(
        scenario_key
    )

    if start_time is None:
        return 0.0

    return max(
        0.0,
        time.monotonic() - start_time,
    )


def _enum_value(
    value,
) -> str:
    """
    Convierte enums y cadenas en texto.
    """

    enum_value = getattr(
        value,
        "value",
        value,
    )

    return str(enum_value)


def _scenario_label(
    scenario: ScenarioType,
) -> str:
    if scenario == ScenarioType.MARITIME_SAR:
        return "Maritime SAR"

    return "Wildfire"


def _utc_now_iso() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .isoformat(
            timespec="seconds"
        )
        .replace(
            "+00:00",
            "Z",
        )
    )