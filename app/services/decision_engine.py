from app.models.recommendation import (
    MissionStatus,
    OperationalRecommendation,
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
from app.services.simulator import get_simulated_assets
from app.services.wildfire_events import get_wildfire_events


def get_operational_recommendations(
) -> list[OperationalRecommendation]:
    events = get_wildfire_events()
    assets = get_simulated_assets()

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
        evaluation = priority_evaluator.evaluate(event)

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

    existing_assignments: dict[
        str,
        AssignmentResult,
    ] = {}

    reserved_asset_ids: set[str] = set()

    # Conserva las misiones que siguen siendo válidas.
    for asset in assets:
        mission = get_active_mission(asset.id)

        if mission is None:
            continue

        event = events_by_id.get(mission.event_id)

        if event is None:
            continue

        existing_assignment = assignment_engine.assign(
            event=event,
            assets=[asset],
        )

        if existing_assignment is None:
            continue

        existing_assignments[event.id] = (
            existing_assignment
        )

        reserved_asset_ids.add(asset.id)

    recommendations: list[OperationalRecommendation] = []
    assigned_asset_ids: set[str] = set()

    for event, priority_evaluation in evaluated_events:
        assignment = existing_assignments.get(event.id)

        # Solo busca un nuevo dron si el incendio
        # todavía no tiene una misión válida.
        if assignment is None:
            candidate_assets = [
                asset
                for asset in assets
                if asset.id not in assigned_asset_ids
                and asset.id not in reserved_asset_ids
            ]

            assignment = assignment_engine.assign(
                event=event,
                assets=candidate_assets,
            )

        if assignment is None:
            recommendations.append(
                OperationalRecommendation(
                    id=f"recommendation-{event.id}",
                    title="No aerial resource available",
                    action=(
                        "Keep the incident in the operational queue "
                        "and request an additional aerial resource."
                    ),
                    reason=(
                        f"{priority_evaluation.reason} "
                        "No remaining drone meets the availability, "
                        "telemetry and minimum battery requirements."
                    ),
                    priority=priority_evaluation.priority,
                    related_event_id=event.id,
                    estimated_response_minutes=0,
                    assigned_asset_name=None,
                    priority_score=priority_evaluation.score,
                    distance_km=None,
                    mission_status=MissionStatus.PENDING,
                )
            )

            continue

        asset = assignment.asset

        if asset.telemetry is not None:
            assign_mission(
                asset_id=asset.id,
                event_id=event.id,
                start_latitude=asset.telemetry.latitude,
                start_longitude=asset.telemetry.longitude,
                target_latitude=event.latitude,
                target_longitude=event.longitude,
                cruise_speed_mps=asset.telemetry.speed,
            )

        assigned_asset_ids.add(asset.id)

        mission_status = (
            MissionStatus.AT_TARGET
            if assignment.distance_km <= 0.05
            else MissionStatus.EN_ROUTE
        )

        recommendations.append(
            OperationalRecommendation(
                id=f"recommendation-{event.id}",
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
                priority=priority_evaluation.priority,
                related_event_id=event.id,
                estimated_response_minutes=(
                    assignment.estimated_response_minutes
                ),
                assigned_asset_name=asset.name,
                priority_score=priority_evaluation.score,
                distance_km=assignment.distance_km,
                mission_status=mission_status,
            )
        )

    # Elimina misiones antiguas que ya no estén asignadas.
    keep_only_missions(assigned_asset_ids)

    return recommendations