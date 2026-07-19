import math

from app.models.detection import DetectionStatus, SensorDetection
from app.models.recommendation import (
    MissionStatus,
    OperationalRecommendation,
    RecommendationPriority,
)
from app.services.assignment_engine import (
    AssignmentEngine,
    AssignmentResult,
)
from app.services.mission_control import (
    assign_mission,
    get_active_mission,
    keep_only_missions,
)
from app.services.priority_evaluator import PriorityEvaluator
from app.services.sensor_detection_engine import (
    get_active_detections,
)
from app.services.simulator import get_simulated_assets
from app.services.wildfire_events import get_wildfire_events


_RESCUE_EVENT_PREFIX = "rescue-"

# Se considera que el recurso ha llegado cuando está
# a 50 metros o menos de la víctima.
_RESCUE_ARRIVAL_DISTANCE_KM = 0.05

# Velocidad mínima utilizada durante la respuesta.
_RESCUE_CRUISE_SPEED_MPS = 14.0


def get_operational_recommendations(
) -> list[OperationalRecommendation]:
    """
    Genera las recomendaciones del escenario Wildfire.

    Antes de una detección confirmada, los recursos
    responden a los incendios.

    Cuando el sensor confirma una persona, el dron que
    produjo la detección abandona la búsqueda y se dirige
    a las coordenadas de la víctima.
    """

    events = get_wildfire_events()
    assets = get_simulated_assets()

    detections = get_active_detections()

    confirmed_detections = {
        detection.related_event_id: detection
        for detection in detections
        if (
            detection.status
            == DetectionStatus.CONFIRMED
        )
    }

    assets_by_id = {
        asset.id: asset
        for asset in assets
    }

    priority_evaluator = PriorityEvaluator()
    assignment_engine = AssignmentEngine()

    active_events = [
        event
        for event in events
        if event.active
    ]

    events_by_id = {
        event.id: event
        for event in active_events
    }

    evaluated_events = []

    for event in active_events:
        evaluation = priority_evaluator.evaluate(
            event
        )

        evaluated_events.append(
            (
                event,
                evaluation,
            )
        )

    # Los incidentes más graves reciben recursos primero.
    evaluated_events.sort(
        key=lambda item: item[1].score,
        reverse=True,
    )

    # Los drones que han confirmado una víctima quedan
    # reservados para la respuesta de rescate.
    rescue_asset_ids = {
        detection.source_asset_id
        for detection in confirmed_detections.values()
    }

    existing_assignments: dict[
        str,
        AssignmentResult,
    ] = {}

    reserved_asset_ids: set[str] = set(
        rescue_asset_ids
    )

    # Conserva las misiones normales que siguen
    # siendo válidas.
    for asset in assets:
        mission = get_active_mission(
            asset.id
        )

        if mission is None:
            continue

        if asset.id in rescue_asset_ids:
            continue

        if _is_rescue_mission(
            mission.event_id
        ):
            continue

        event = events_by_id.get(
            mission.event_id
        )

        if event is None:
            continue

        existing_assignment = (
            assignment_engine.assign(
                event=event,
                assets=[asset],
            )
        )

        if existing_assignment is None:
            continue

        existing_assignments[event.id] = (
            existing_assignment
        )

        reserved_asset_ids.add(
            asset.id
        )

    recommendations: list[
        OperationalRecommendation
    ] = []

    assigned_asset_ids: set[str] = set()

    for (
        event,
        priority_evaluation,
    ) in evaluated_events:
        detection = confirmed_detections.get(
            event.id
        )

        if detection is not None:
            rescue_asset = assets_by_id.get(
                detection.source_asset_id
            )

            recommendation = (
                _build_rescue_recommendation(
                    event=event,
                    detection=detection,
                    asset=rescue_asset,
                    priority_score=(
                        priority_evaluation.score
                    ),
                )
            )

            recommendations.append(
                recommendation
            )

            if rescue_asset is not None:
                assigned_asset_ids.add(
                    rescue_asset.id
                )

            continue

        assignment = existing_assignments.get(
            event.id
        )

        # Busca un dron nuevo únicamente si el incidente
        # todavía no tiene una misión válida.
        if assignment is None:
            candidate_assets = [
                asset
                for asset in assets
                if (
                    asset.id
                    not in assigned_asset_ids
                    and asset.id
                    not in reserved_asset_ids
                )
            ]

            assignment = assignment_engine.assign(
                event=event,
                assets=candidate_assets,
            )

        if assignment is None:
            recommendations.append(
                OperationalRecommendation(
                    id=(
                        f"recommendation-{event.id}"
                    ),
                    title=(
                        "No aerial resource available"
                    ),
                    action=(
                        "Keep the incident in the "
                        "operational queue and request "
                        "an additional aerial resource."
                    ),
                    reason=(
                        f"{priority_evaluation.reason} "
                        "No remaining drone meets the "
                        "availability, telemetry and "
                        "minimum battery requirements."
                    ),
                    priority=(
                        priority_evaluation.priority
                    ),
                    related_event_id=event.id,
                    estimated_response_minutes=0,
                    assigned_asset_name=None,
                    priority_score=(
                        priority_evaluation.score
                    ),
                    distance_km=None,
                    mission_status=(
                        MissionStatus.PENDING
                    ),
                )
            )

            continue

        asset = assignment.asset

        if asset.telemetry is not None:
            assign_mission(
                asset_id=asset.id,
                event_id=event.id,
                start_latitude=(
                    asset.telemetry.latitude
                ),
                start_longitude=(
                    asset.telemetry.longitude
                ),
                target_latitude=event.latitude,
                target_longitude=event.longitude,
                cruise_speed_mps=max(
                    1.0,
                    asset.telemetry.speed,
                ),
            )

        assigned_asset_ids.add(
            asset.id
        )

        mission_status = (
            MissionStatus.AT_TARGET
            if (
                assignment.distance_km
                <= _RESCUE_ARRIVAL_DISTANCE_KM
            )
            else MissionStatus.EN_ROUTE
        )

        recommendations.append(
            OperationalRecommendation(
                id=(
                    f"recommendation-{event.id}"
                ),
                title=f"Deploy {asset.name}",
                action=(
                    f"Dispatch {asset.name} "
                    f"to the incident at "
                    f"{event.latitude:.4f}, "
                    f"{event.longitude:.4f}."
                ),
                reason=(
                    f"{priority_evaluation.reason} "
                    f"{asset.name} was selected "
                    f"with {asset.battery}% battery "
                    f"at a distance of "
                    f"{assignment.distance_km:.2f} km."
                ),
                priority=(
                    priority_evaluation.priority
                ),
                related_event_id=event.id,
                estimated_response_minutes=(
                    assignment
                    .estimated_response_minutes
                ),
                assigned_asset_name=asset.name,
                priority_score=(
                    priority_evaluation.score
                ),
                distance_km=(
                    assignment.distance_km
                ),
                mission_status=mission_status,
            )
        )

    # Elimina misiones antiguas que ya no pertenecen
    # a una asignación activa.
    keep_only_missions(
        assigned_asset_ids
    )

    return recommendations


def _build_rescue_recommendation(
    event,
    detection: SensorDetection,
    asset,
    priority_score: int,
) -> OperationalRecommendation:
    """
    Construye la recomendación generada después
    de confirmar una víctima.
    """

    if (
        asset is None
        or asset.telemetry is None
    ):
        return OperationalRecommendation(
            id=(
                f"recommendation-rescue-{event.id}"
            ),
            title=(
                "Confirmed victim — resource unavailable"
            ),
            action=(
                "Request an immediate rescue resource "
                "for the confirmed coordinates."
            ),
            reason=(
                "The person detection is confirmed, "
                "but the detecting asset currently has "
                "no valid telemetry."
            ),
            priority=RecommendationPriority.CRITICAL,
            related_event_id=event.id,
            estimated_response_minutes=0,
            assigned_asset_name=(
                detection.source_asset_name
            ),
            priority_score=max(
                priority_score,
                95,
            ),
            distance_km=None,
            mission_status=MissionStatus.PENDING,
        )

    distance_km = _calculate_distance_km(
        latitude_1=(
            asset.telemetry.latitude
        ),
        longitude_1=(
            asset.telemetry.longitude
        ),
        latitude_2=detection.latitude,
        longitude_2=detection.longitude,
    )

    rescue_event_id = (
        f"{_RESCUE_EVENT_PREFIX}{event.id}"
    )

    current_mission = get_active_mission(
        asset.id
    )

    rescue_mission_already_active = (
        current_mission is not None
        and current_mission.event_id
        == rescue_event_id
        and current_mission.target_latitude
        == detection.latitude
        and current_mission.target_longitude
        == detection.longitude
    )

    rescue_speed_mps = max(
        _RESCUE_CRUISE_SPEED_MPS,
        asset.telemetry.speed,
    )

    assign_mission(
        asset_id=asset.id,
        event_id=rescue_event_id,
        start_latitude=(
            asset.telemetry.latitude
        ),
        start_longitude=(
            asset.telemetry.longitude
        ),
        target_latitude=detection.latitude,
        target_longitude=detection.longitude,
        cruise_speed_mps=rescue_speed_mps,
    )

    arrived = (
        distance_km
        <= _RESCUE_ARRIVAL_DISTANCE_KM
    )

    if arrived:
        mission_status = (
            MissionStatus.RESCUE_COMPLETED
        )

        title = "Rescue position reached"

        action = (
            f"{asset.name} has reached the confirmed "
            "victim coordinates. Maintain overwatch "
            "and complete the rescue handoff."
        )

        estimated_response_minutes = 0

    elif rescue_mission_already_active:
        mission_status = MissionStatus.EN_ROUTE

        title = (
            f"{asset.name} responding to victim"
        )

        action = (
            f"Continue directly to the confirmed "
            f"victim at {detection.latitude:.6f}, "
            f"{detection.longitude:.6f}."
        )

        estimated_response_minutes = (
            _estimated_minutes(
                distance_km=distance_km,
                speed_mps=rescue_speed_mps,
            )
        )

    else:
        mission_status = (
            MissionStatus.VICTIM_LOCATED
        )

        title = "Confirmed victim located"

        action = (
            f"Interrupt the search pattern and dispatch "
            f"{asset.name} to {detection.latitude:.6f}, "
            f"{detection.longitude:.6f}."
        )

        estimated_response_minutes = (
            _estimated_minutes(
                distance_km=distance_km,
                speed_mps=rescue_speed_mps,
            )
        )

    return OperationalRecommendation(
        id=(
            f"recommendation-rescue-{event.id}"
        ),
        title=title,
        action=action,
        reason=(
            f"{detection.source_asset_name} confirmed "
            f"a person using "
            f"{detection.sensor_type.value.replace('_', ' ')} "
            f"with {detection.confidence_percent:.1f}% "
            "confidence. The detecting asset is now "
            "reserved for the rescue response."
        ),
        priority=RecommendationPriority.CRITICAL,
        related_event_id=event.id,
        estimated_response_minutes=(
            estimated_response_minutes
        ),
        assigned_asset_name=asset.name,
        priority_score=max(
            priority_score,
            95,
        ),
        distance_km=round(
            distance_km,
            2,
        ),
        mission_status=mission_status,
    )


def _estimated_minutes(
    distance_km: float,
    speed_mps: float,
) -> int:
    """
    Calcula el tiempo estimado de llegada.
    """

    if distance_km <= 0:
        return 0

    distance_m = (
        distance_km * 1000.0
    )

    seconds = distance_m / max(
        1.0,
        speed_mps,
    )

    return max(
        1,
        math.ceil(
            seconds / 60.0
        ),
    )


def _is_rescue_mission(
    event_id: str,
) -> bool:
    return event_id.startswith(
        _RESCUE_EVENT_PREFIX
    )


def _calculate_distance_km(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """
    Calcula la distancia entre dos coordenadas
    mediante Haversine.
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