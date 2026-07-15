import math

from app.models.asset import Asset, AssetType
from app.models.event import OperationalEvent
from app.models.recommendation import (
    MissionStatus,
    OperationalRecommendation,
    RecommendationPriority,
)
from app.services.maritime_events import get_maritime_events
from app.services.maritime_simulator import (
    SIMULATION_TIME_SCALE,
    get_maritime_assets,
)
from app.services.priority_evaluator import PriorityEvaluator


_DRONE_LOCATION_THRESHOLD_KM = 0.08
_BOAT_RESCUE_THRESHOLD_KM = 0.05


def get_maritime_recommendations(
) -> list[OperationalRecommendation]:
    events = [
        event
        for event in get_maritime_events()
        if event.active
    ]

    if not events:
        return []

    assets = get_maritime_assets()

    drone = _find_asset(
        assets=assets,
        asset_type=AssetType.AERIAL_DRONE,
    )

    boat = _find_asset(
        assets=assets,
        asset_type=AssetType.MARITIME_VEHICLE,
    )

    priority_evaluator = PriorityEvaluator()
    recommendations: list[
        OperationalRecommendation
    ] = []

    for event in events:
        evaluation = priority_evaluator.evaluate(event)

        drone_distance_km = _get_asset_distance(
            asset=drone,
            event=event,
        )

        recommendations.append(
            _build_drone_recommendation(
                event=event,
                drone=drone,
                distance_km=drone_distance_km,
                priority=evaluation.priority,
                priority_score=evaluation.score,
                priority_reason=evaluation.reason,
            )
        )

        recommendations.append(
            _build_boat_recommendation(
                event=event,
                boat=boat,
                distance_km=_get_asset_distance(
                    asset=boat,
                    event=event,
                ),
                victim_confirmed=(
                    drone_distance_km is not None
                    and drone_distance_km
                    <= _DRONE_LOCATION_THRESHOLD_KM
                ),
                priority=evaluation.priority,
                priority_score=evaluation.score,
                priority_reason=evaluation.reason,
            )
        )

    return recommendations


def _find_asset(
    assets: list[Asset],
    asset_type: AssetType,
) -> Asset | None:
    for asset in assets:
        if (
            asset.asset_type == asset_type
            and asset.telemetry is not None
        ):
            return asset

    return None


def _get_asset_distance(
    asset: Asset | None,
    event: OperationalEvent,
) -> float | None:
    if asset is None or asset.telemetry is None:
        return None

    return _calculate_distance_km(
        latitude_1=asset.telemetry.latitude,
        longitude_1=asset.telemetry.longitude,
        latitude_2=event.latitude,
        longitude_2=event.longitude,
    )


def _build_drone_recommendation(
    event: OperationalEvent,
    drone: Asset | None,
    distance_km: float | None,
    priority: RecommendationPriority,
    priority_score: int,
    priority_reason: str,
) -> OperationalRecommendation:
    if (
        drone is None
        or drone.telemetry is None
        or distance_km is None
    ):
        return OperationalRecommendation(
            id=f"recommendation-{event.id}-drone",
            title="SAR drone unavailable",
            action=(
                "Request an additional aerial search "
                "resource."
            ),
            reason=(
                f"{priority_reason} "
                "No aerial SAR asset is available."
            ),
            priority=priority,
            related_event_id=event.id,
            estimated_response_minutes=0,
            assigned_asset_name=None,
            priority_score=priority_score,
            distance_km=None,
            mission_status=MissionStatus.PENDING,
        )

    victim_located = (
        distance_km
        <= _DRONE_LOCATION_THRESHOLD_KM
    )

    if victim_located:
        return OperationalRecommendation(
            id=f"recommendation-{event.id}-drone",
            title=f"Victim located by {drone.name}",
            action=(
                f"Maintain {drone.name} above the victim "
                "and continuously transmit the confirmed "
                "position to the rescue boat."
            ),
            reason=(
                f"{priority_reason} "
                "The aerial asset has reached the target "
                "and confirmed the victim location."
            ),
            priority=priority,
            related_event_id=event.id,
            estimated_response_minutes=0,
            assigned_asset_name=drone.name,
            priority_score=priority_score,
            distance_km=distance_km,
            mission_status=(
                MissionStatus.VICTIM_LOCATED
            ),
        )

    estimated_minutes = _estimate_response_minutes(
        distance_km=distance_km,
        speed_mps=drone.telemetry.speed,
    )

    return OperationalRecommendation(
        id=f"recommendation-{event.id}-drone",
        title=f"Deploy {drone.name}",
        action=(
            f"Send {drone.name} to locate the victim "
            "and establish continuous visual tracking."
        ),
        reason=(
            f"{priority_reason} "
            f"The drone is {distance_km:.2f} km from "
            "the reported position."
        ),
        priority=priority,
        related_event_id=event.id,
        estimated_response_minutes=estimated_minutes,
        assigned_asset_name=drone.name,
        priority_score=priority_score,
        distance_km=distance_km,
        mission_status=MissionStatus.EN_ROUTE,
    )


def _build_boat_recommendation(
    event: OperationalEvent,
    boat: Asset | None,
    distance_km: float | None,
    victim_confirmed: bool,
    priority: RecommendationPriority,
    priority_score: int,
    priority_reason: str,
) -> OperationalRecommendation:
    if (
        boat is None
        or boat.telemetry is None
        or distance_km is None
    ):
        return OperationalRecommendation(
            id=f"recommendation-{event.id}-boat",
            title="Rescue boat unavailable",
            action=(
                "Request the nearest maritime rescue "
                "unit."
            ),
            reason=(
                f"{priority_reason} "
                "No maritime rescue asset is available."
            ),
            priority=priority,
            related_event_id=event.id,
            estimated_response_minutes=0,
            assigned_asset_name=None,
            priority_score=priority_score,
            distance_km=None,
            mission_status=MissionStatus.PENDING,
        )

    rescue_completed = (
        distance_km
        <= _BOAT_RESCUE_THRESHOLD_KM
    )

    if rescue_completed:
        return OperationalRecommendation(
            id=f"recommendation-{event.id}-boat",
            title=f"Rescue completed by {boat.name}",
            action=(
                "Secure the rescued person, begin medical "
                "assessment and return to the designated "
                "safe harbor."
            ),
            reason=(
                f"{priority_reason} "
                "The rescue boat has reached the confirmed "
                "victim position."
            ),
            priority=priority,
            related_event_id=event.id,
            estimated_response_minutes=0,
            assigned_asset_name=boat.name,
            priority_score=priority_score,
            distance_km=distance_km,
            mission_status=(
                MissionStatus.RESCUE_COMPLETED
            ),
        )

    if victim_confirmed:
        title = f"Navigate {boat.name} to confirmed victim"
        action = (
            f"Guide {boat.name} using the confirmed "
            "coordinates transmitted by the SAR drone."
        )
        confirmation_reason = (
            " The victim position has been confirmed "
            "by the aerial unit."
        )
    else:
        title = f"Dispatch {boat.name}"
        action = (
            f"Send {boat.name} toward the reported "
            "coordinates while awaiting aerial "
            "confirmation."
        )
        confirmation_reason = (
            " The aerial unit is still confirming "
            "the exact victim position."
        )

    estimated_minutes = _estimate_response_minutes(
        distance_km=distance_km,
        speed_mps=boat.telemetry.speed,
    )

    return OperationalRecommendation(
        id=f"recommendation-{event.id}-boat",
        title=title,
        action=action,
        reason=(
            f"{priority_reason}"
            f"{confirmation_reason} "
            f"The boat is {distance_km:.2f} km from "
            "the target."
        ),
        priority=priority,
        related_event_id=event.id,
        estimated_response_minutes=estimated_minutes,
        assigned_asset_name=boat.name,
        priority_score=priority_score,
        distance_km=distance_km,
        mission_status=MissionStatus.EN_ROUTE,
    )


def _estimate_response_minutes(
    distance_km: float,
    speed_mps: float,
) -> int:
    if distance_km <= 0.05:
        return 0

    if speed_mps <= 0:
        return 0

    effective_speed_mps = (
        speed_mps * SIMULATION_TIME_SCALE
    )

    distance_meters = distance_km * 1000
    seconds = distance_meters / effective_speed_mps
    minutes = seconds / 60

    return max(1, round(minutes))


def _calculate_distance_km(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    earth_radius_km = 6371.0

    latitude_1_radians = math.radians(latitude_1)
    latitude_2_radians = math.radians(latitude_2)

    latitude_delta = math.radians(
        latitude_2 - latitude_1
    )

    longitude_delta = math.radians(
        longitude_2 - longitude_1
    )

    haversine_value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_1_radians)
        * math.cos(latitude_2_radians)
        * math.sin(longitude_delta / 2) ** 2
    )

    angular_distance = 2 * math.atan2(
        math.sqrt(haversine_value),
        math.sqrt(1 - haversine_value),
    )

    return round(
        earth_radius_km * angular_distance,
        3,
    )