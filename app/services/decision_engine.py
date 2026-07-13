from app.models.recommendation import OperationalRecommendation
from app.services.assignment_engine import AssignmentEngine
from app.services.priority_evaluator import PriorityEvaluator
from app.services.simulator import get_simulated_assets
from app.services.wildfire_events import get_wildfire_events


def get_operational_recommendations(
) -> list[OperationalRecommendation]:
    events = get_wildfire_events()
    assets = get_simulated_assets()

    priority_evaluator = PriorityEvaluator()
    assignment_engine = AssignmentEngine()

    recommendations: list[OperationalRecommendation] = []

    for event in events:
        if not event.active:
            continue

        priority_evaluation = priority_evaluator.evaluate(event)

        assignment = assignment_engine.assign(
            event=event,
            assets=assets,
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
                        "No drone currently meets the availability, "
                        "telemetry and minimum battery requirements."
                    ),
                    priority=priority_evaluation.priority,
                    related_event_id=event.id,
                    estimated_response_minutes=0,
                    assigned_asset_name=None,
                    priority_score=priority_evaluation.score,
                    distance_km=None,
                )
            )

            continue

        recommendations.append(
            OperationalRecommendation(
                id=f"recommendation-{event.id}",
                title=f"Deploy {assignment.asset.name}",
                action=(
                    f"Dispatch {assignment.asset.name} "
                    f"to the incident at "
                    f"{event.latitude:.4f}, "
                    f"{event.longitude:.4f}."
                ),
                reason=(
                    f"{priority_evaluation.reason} "
                    f"{assignment.asset.name} was selected "
                    f"with {assignment.asset.battery}% battery "
                    f"at a distance of "
                    f"{assignment.distance_km:.2f} km."
                ),
                priority=priority_evaluation.priority,
                related_event_id=event.id,
                estimated_response_minutes=(
                    assignment.estimated_response_minutes
                ),
                assigned_asset_name=assignment.asset.name,
                priority_score=priority_evaluation.score,
                distance_km=assignment.distance_km,
            )
        )

    return recommendations