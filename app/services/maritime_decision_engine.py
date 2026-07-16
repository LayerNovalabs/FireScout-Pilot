import math

from app.models.asset import Asset, AssetType
from app.models.event import OperationalEvent
from app.models.recommendation import (
    MissionStatus,
    OperationalRecommendation,
    RecommendationPriority,
)
from app.models.search_area import SearchArea
from app.services.maritime_events import get_maritime_events
from app.services.maritime_simulator import (
    SIMULATION_TIME_SCALE,
    get_maritime_assets,
)
from app.services.priority_evaluator import PriorityEvaluator
from app.services.scenario_manager import ScenarioType
from app.services.search_area_engine import SearchAreaEngine


_DRONE_ON_STATION_THRESHOLD_KM = 0.08
_BOAT_STAGING_THRESHOLD_KM = 0.10


def get_maritime_recommendations(
) -> list[OperationalRecommendation]:
    """
    Genera recomendaciones para el escenario Maritime SAR.

    El dron y la embarcación se dirigen al centro calculado
    de la zona de búsqueda.

    Alcanzar el área no significa que la víctima haya sido
    localizada ni que el rescate haya finalizado.
    """

    events = [
        event
        for event in get_maritime_events()
        if event.active
    ]

    if not events:
        return []

    search_areas = SearchAreaEngine().get_search_areas(
        ScenarioType.MARITIME_SAR
    )

    areas_by_event_id = {
        area.related_event_id: area
        for area in search_areas
    }

    assets = get_maritime_assets()

    drone = _find_asset(
        assets,
        AssetType.AERIAL_DRONE,
    )

    boat = _find_asset(
        assets,
        AssetType.MARITIME_VEHICLE,
    )

    priority_evaluator = PriorityEvaluator()

    recommendations: list[
        OperationalRecommendation
    ] = []

    for event in events:
        area = areas_by_event_id.get(
            event.id
        )

        if area is None:
            continue

        evaluation = priority_evaluator.evaluate(
            event
        )

        drone_distance_km = (
            _get_asset_distance_to_area(
                drone,
                area,
            )
        )

        boat_distance_km = (
            _get_asset_distance_to_area(
                boat,
                area,
            )
        )

        recommendations.append(
            _build_drone_recommendation(
                event=event,
                area=area,
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
                area=area,
                boat=boat,
                distance_km=boat_distance_km,
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
    """
    Localiza un activo de un tipo determinado
    que disponga de telemetría.
    """

    for asset in assets:
        if (
            asset.asset_type == asset_type
            and asset.telemetry is not None
        ):
            return asset

    return None


def _get_asset_distance_to_area(
    asset: Asset | None,
    area: SearchArea,
) -> float | None:
    """
    Calcula la distancia entre un activo y el centro
    estimado de una zona de búsqueda.
    """

    if (
        asset is None
        or asset.telemetry is None
    ):
        return None

    return _calculate_distance_km(
        latitude_1=asset.telemetry.latitude,
        longitude_1=asset.telemetry.longitude,
        latitude_2=(
            area.estimated_center.latitude
        ),
        longitude_2=(
            area.estimated_center.longitude
        ),
    )


def _build_drone_recommendation(
    event: OperationalEvent,
    area: SearchArea,
    drone: Asset | None,
    distance_km: float | None,
    priority: RecommendationPriority,
    priority_score: int,
    priority_reason: str,
) -> OperationalRecommendation:
    """
    Genera la recomendación operativa del dron SAR.
    """

    if (
        drone is None
        or drone.telemetry is None
        or distance_km is None
    ):
        return OperationalRecommendation(
            id=(
                f"recommendation-"
                f"{event.id}-drone"
            ),
            title="SAR drone unavailable",
            action=(
                "Request an additional aerial "
                "search resource."
            ),
            reason=(
                f"{priority_reason} "
                "No aerial SAR asset is available "
                "to cover the calculated search area."
            ),
            priority=priority,
            related_event_id=event.id,
            estimated_response_minutes=0,
            assigned_asset_name=None,
            priority_score=priority_score,
            distance_km=None,
            mission_status=MissionStatus.PENDING,
        )

    on_station = (
        distance_km
        <= _DRONE_ON_STATION_THRESHOLD_KM
    )

    if on_station:
        return OperationalRecommendation(
            id=(
                f"recommendation-"
                f"{event.id}-drone"
            ),
            title=f"{drone.name} on station",
            action=(
                "Hold above the estimated search-area "
                "center and await the automated coverage "
                "pattern planned for Day 7."
            ),
            reason=(
                f"{priority_reason} "
                "The drone has reached the calculated "
                f"search ellipse with "
                f"{area.confidence:.0%} confidence. "
                "The victim has not yet been detected."
            ),
            priority=priority,
            related_event_id=event.id,
            estimated_response_minutes=0,
            assigned_asset_name=drone.name,
            priority_score=priority_score,
            distance_km=distance_km,
            mission_status=MissionStatus.SEARCHING,
        )

    estimated_minutes = (
        _estimate_response_minutes(
            distance_km,
            drone.telemetry.speed,
        )
    )

    return OperationalRecommendation(
        id=(
            f"recommendation-"
            f"{event.id}-drone"
        ),
        title=(
            f"Deploy {drone.name} "
            "to calculated search area"
        ),
        action=(
            f"Send {drone.name} to the estimated "
            f"center at "
            f"{area.estimated_center.latitude:.4f}, "
            f"{area.estimated_center.longitude:.4f}."
        ),
        reason=(
            f"{priority_reason} "
            "Wind, current and waves project the "
            f"search center "
            f"{area.displacement_m:.0f} m from the "
            "last known position. "
            f"The drone is {distance_km:.2f} km away."
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
    area: SearchArea,
    boat: Asset | None,
    distance_km: float | None,
    priority: RecommendationPriority,
    priority_score: int,
    priority_reason: str,
) -> OperationalRecommendation:
    """
    Genera la recomendación operativa de la embarcación.
    """

    if (
        boat is None
        or boat.telemetry is None
        or distance_km is None
    ):
        return OperationalRecommendation(
            id=(
                f"recommendation-"
                f"{event.id}-boat"
            ),
            title="Rescue boat unavailable",
            action=(
                "Request the nearest maritime "
                "rescue unit."
            ),
            reason=(
                f"{priority_reason} "
                "No maritime asset is available "
                "to stage near the calculated "
                "search area."
            ),
            priority=priority,
            related_event_id=event.id,
            estimated_response_minutes=0,
            assigned_asset_name=None,
            priority_score=priority_score,
            distance_km=None,
            mission_status=MissionStatus.PENDING,
        )

    staged = (
        distance_km
        <= _BOAT_STAGING_THRESHOLD_KM
    )

    if staged:
        return OperationalRecommendation(
            id=(
                f"recommendation-"
                f"{event.id}-boat"
            ),
            title=(
                f"{boat.name} staged "
                "near search area"
            ),
            action=(
                "Maintain a safe standby position "
                "and wait for the drone to report "
                "a confirmed victim location."
            ),
            reason=(
                f"{priority_reason} "
                "The boat is positioned near the "
                "probabilistic search ellipse. "
                "Rescue is not complete because "
                "the victim has not yet been located."
            ),
            priority=priority,
            related_event_id=event.id,
            estimated_response_minutes=0,
            assigned_asset_name=boat.name,
            priority_score=priority_score,
            distance_km=distance_km,
            mission_status=MissionStatus.AT_TARGET,
        )

    estimated_minutes = (
        _estimate_response_minutes(
            distance_km,
            boat.telemetry.speed,
        )
    )

    return OperationalRecommendation(
        id=(
            f"recommendation-"
            f"{event.id}-boat"
        ),
        title=(
            f"Stage {boat.name} "
            "near search area"
        ),
        action=(
            f"Navigate {boat.name} toward the "
            "calculated search-area center while "
            "maintaining safe separation from "
            "aerial search."
        ),
        reason=(
            f"{priority_reason} "
            f"The boat is {distance_km:.2f} km "
            "from the projected search center and "
            "should be ready to respond after "
            "aerial confirmation."
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
    """
    Calcula el tiempo estimado de llegada teniendo
    en cuenta la escala temporal de la simulación.
    """

    if (
        distance_km <= 0.05
        or speed_mps <= 0
    ):
        return 0

    effective_speed_mps = (
        speed_mps
        * SIMULATION_TIME_SCALE
    )

    seconds = (
        distance_km
        * 1000
        / effective_speed_mps
    )

    return max(
        1,
        round(seconds / 60),
    )


def _calculate_distance_km(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """
    Calcula la distancia entre dos coordenadas mediante
    la fórmula de Haversine.
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
            latitude_delta / 2
        ) ** 2
        + math.cos(latitude_1_radians)
        * math.cos(latitude_2_radians)
        * math.sin(
            longitude_delta / 2
        ) ** 2
    )

    angular_distance = 2 * math.atan2(
        math.sqrt(haversine_value),
        math.sqrt(
            1 - haversine_value
        ),
    )

    return round(
        earth_radius_km
        * angular_distance,
        3,
    )