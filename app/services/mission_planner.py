import math

from app.models.mission_plan import (
    MissionPlanStatus,
    SearchMissionPlan,
    SearchPattern,
    SearchWaypoint,
)
from app.models.search_area import GeoPoint, SearchArea
from app.services.scenario_manager import (
    ScenarioType,
    get_active_scenario,
)
from app.services.search_area_engine import SearchAreaEngine


_EARTH_RADIUS_M = 6_371_000.0

# Margen para que los waypoints no queden
# exactamente sobre el borde de la elipse.
_ELLIPSE_EDGE_MARGIN = 0.90


# Asignaciones exclusivas para Wildfire.
_WILDFIRE_ASSET_ASSIGNMENTS: dict[
    str,
    tuple[str, str],
] = {
    "event-001": (
        "sim-001",
        "Simulator Alpha",
    ),
    "event-002": (
        "sim-002",
        "Simulator Bravo",
    ),
}


# Asignación exclusiva para Maritime SAR.
_MARITIME_ASSET_ASSIGNMENT = (
    "sar-drone-001",
    "SAR Drone One",
)


class MissionPlanner:
    """
    Genera patrones automáticos de búsqueda dentro
    de las zonas probabilísticas calculadas.

    Cada misión queda asignada a un único dron.
    Un dron no puede ejecutar simultáneamente
    los planes de varios eventos.
    """

    def __init__(
        self,
        search_area_engine: SearchAreaEngine | None = None,
    ) -> None:
        self._search_area_engine = (
            search_area_engine or SearchAreaEngine()
        )

    def get_mission_plans(
        self,
        scenario: ScenarioType,
    ) -> list[SearchMissionPlan]:
        """
        Genera únicamente los planes que disponen
        de un activo asignado.
        """

        search_areas = (
            self._search_area_engine.get_search_areas(
                scenario
            )
        )

        plans: list[SearchMissionPlan] = []

        for search_area in search_areas:
            assignment = _get_asset_assignment(
                search_area
            )

            if assignment is None:
                # No se crea una misión automática
                # cuando no existe un dron disponible.
                continue

            (
                assigned_asset_id,
                assigned_asset_name,
            ) = assignment

            plan = self.create_plan(
                search_area=search_area,
                assigned_asset_id=assigned_asset_id,
                assigned_asset_name=assigned_asset_name,
            )

            plans.append(plan)

        return plans

    def create_plan(
        self,
        search_area: SearchArea,
        assigned_asset_id: str,
        assigned_asset_name: str,
    ) -> SearchMissionPlan:
        """
        Genera un patrón de líneas paralelas dentro
        de una elipse de búsqueda.
        """

        (
            desired_spacing_m,
            altitude_m,
            search_speed_mps,
        ) = _scenario_parameters(
            search_area.scenario
        )

        cross_track_limit_m = (
            search_area.semi_minor_axis_m
            * _ELLIPSE_EDGE_MARGIN
        )

        track_count = max(
            3,
            math.ceil(
                (
                    2.0
                    * cross_track_limit_m
                )
                / desired_spacing_m
            )
            + 1,
        )

        actual_spacing_m = (
            2.0
            * cross_track_limit_m
            / (track_count - 1)
        )

        cross_track_offsets = [
            -cross_track_limit_m
            + index * actual_spacing_m
            for index in range(track_count)
        ]

        waypoints: list[SearchWaypoint] = []

        for (
            track_index,
            cross_track_offset_m,
        ) in enumerate(cross_track_offsets):
            normalized_cross_track = (
                cross_track_offset_m
                / search_area.semi_minor_axis_m
            )

            half_track_length_m = (
                search_area.semi_major_axis_m
                * math.sqrt(
                    max(
                        0.0,
                        1.0
                        - normalized_cross_track**2,
                    )
                )
                * _ELLIPSE_EDGE_MARGIN
            )

            if track_index % 2 == 0:
                along_track_offsets = (
                    -half_track_length_m,
                    half_track_length_m,
                )
            else:
                along_track_offsets = (
                    half_track_length_m,
                    -half_track_length_m,
                )

            for (
                endpoint_index,
                along_track_offset_m,
            ) in enumerate(along_track_offsets):
                point = _local_ellipse_point_to_geo(
                    center=(
                        search_area.estimated_center
                    ),
                    along_track_m=(
                        along_track_offset_m
                    ),
                    cross_track_m=(
                        cross_track_offset_m
                    ),
                    orientation_degrees=(
                        search_area.orientation_degrees
                    ),
                )

                if not waypoints:
                    action = "enter_search_area"
                elif (
                    track_index
                    == track_count - 1
                    and endpoint_index == 1
                ):
                    action = "complete_search"
                else:
                    action = "search_track"

                waypoints.append(
                    SearchWaypoint(
                        sequence=len(waypoints),
                        latitude=point.latitude,
                        longitude=point.longitude,
                        altitude_m=altitude_m,
                        action=action,
                    )
                )

        path_length_m = _calculate_path_length_m(
            waypoints
        )

        if search_speed_mps > 0:
            duration_minutes = (
                path_length_m
                / search_speed_mps
                / 60.0
            )
        else:
            duration_minutes = 0.0

        if waypoints:
            entry_point = GeoPoint(
                latitude=waypoints[0].latitude,
                longitude=waypoints[0].longitude,
            )
        else:
            entry_point = (
                search_area.estimated_center
            )

        return SearchMissionPlan(
            id=(
                "mission-plan-"
                f"{search_area.related_event_id}"
            ),
            scenario=search_area.scenario,
            related_event_id=(
                search_area.related_event_id
            ),
            search_area_id=search_area.id,
            assigned_asset_id=assigned_asset_id,
            assigned_asset_name=assigned_asset_name,
            pattern=SearchPattern.PARALLEL_TRACK,
            orientation_degrees=(
                search_area.orientation_degrees
            ),
            track_spacing_m=round(
                actual_spacing_m,
                1,
            ),
            altitude_m=altitude_m,
            entry_point=entry_point,
            waypoints=waypoints,
            waypoint_count=len(waypoints),
            estimated_path_length_m=round(
                path_length_m,
                1,
            ),
            estimated_duration_minutes=round(
                duration_minutes,
                1,
            ),
            current_waypoint_index=0,
            coverage_percent=0.0,
            status=MissionPlanStatus.PLANNED,
            calculation_summary=(
                f"{assigned_asset_name} assigned exclusively "
                f"to {search_area.related_event_id}. "
                f"Parallel-track route with {track_count} passes, "
                f"{actual_spacing_m:.1f} m track spacing "
                f"and {altitude_m:.0f} m search altitude."
            ),
        )


def get_active_mission_plans(
) -> list[SearchMissionPlan]:
    """
    Devuelve los planes del escenario activo.
    """

    return MissionPlanner().get_mission_plans(
        get_active_scenario()
    )


def _get_asset_assignment(
    search_area: SearchArea,
) -> tuple[str, str] | None:
    """
    Devuelve el activo asignado exclusivamente
    a una zona de búsqueda.
    """

    if (
        search_area.scenario
        == ScenarioType.MARITIME_SAR.value
    ):
        return _MARITIME_ASSET_ASSIGNMENT

    return _WILDFIRE_ASSET_ASSIGNMENTS.get(
        search_area.related_event_id
    )


def _scenario_parameters(
    scenario: str,
) -> tuple[float, float, float]:
    """
    Devuelve:

    - separación entre pasadas;
    - altitud;
    - velocidad de búsqueda.
    """

    if scenario == ScenarioType.MARITIME_SAR.value:
        return (
            110.0,
            85.0,
            14.0,
        )

    return (
        85.0,
        95.0,
        12.0,
    )


def _local_ellipse_point_to_geo(
    center: GeoPoint,
    along_track_m: float,
    cross_track_m: float,
    orientation_degrees: float,
) -> GeoPoint:
    """
    Convierte una posición local dentro de la elipse
    en una coordenada geográfica.
    """

    along_north, along_east = (
        _vector_components(
            along_track_m,
            orientation_degrees,
        )
    )

    cross_north, cross_east = (
        _vector_components(
            cross_track_m,
            orientation_degrees + 90.0,
        )
    )

    return _offset_point(
        latitude=center.latitude,
        longitude=center.longitude,
        north_m=(
            along_north
            + cross_north
        ),
        east_m=(
            along_east
            + cross_east
        ),
    )


def _vector_components(
    magnitude: float,
    bearing_degrees: float,
) -> tuple[float, float]:
    """
    Convierte distancia y rumbo en componentes
    norte y este.
    """

    bearing_radians = math.radians(
        bearing_degrees
    )

    north = (
        magnitude
        * math.cos(bearing_radians)
    )

    east = (
        magnitude
        * math.sin(bearing_radians)
    )

    return north, east


def _offset_point(
    latitude: float,
    longitude: float,
    north_m: float,
    east_m: float,
) -> GeoPoint:
    """
    Desplaza una coordenada hacia el norte
    y hacia el este.
    """

    latitude_radians = math.radians(
        latitude
    )

    latitude_delta = (
        north_m / _EARTH_RADIUS_M
    )

    longitude_delta = east_m / (
        _EARTH_RADIUS_M
        * math.cos(latitude_radians)
    )

    return GeoPoint(
        latitude=round(
            latitude
            + math.degrees(latitude_delta),
            6,
        ),
        longitude=round(
            longitude
            + math.degrees(longitude_delta),
            6,
        ),
    )


def _calculate_path_length_m(
    waypoints: list[SearchWaypoint],
) -> float:
    """
    Calcula la longitud total de la ruta.
    """

    total_distance_m = 0.0

    for (
        waypoint_1,
        waypoint_2,
    ) in zip(
        waypoints,
        waypoints[1:],
    ):
        total_distance_m += (
            _calculate_distance_m(
                latitude_1=waypoint_1.latitude,
                longitude_1=waypoint_1.longitude,
                latitude_2=waypoint_2.latitude,
                longitude_2=waypoint_2.longitude,
            )
        )

    return total_distance_m


def _calculate_distance_m(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """
    Calcula la distancia mediante Haversine.
    """

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
        _EARTH_RADIUS_M
        * angular_distance
    )