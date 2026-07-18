import math
from dataclasses import dataclass

from app.models.mission_plan import (
    MissionPlanStatus,
    SearchMissionPlan,
    SearchWaypoint,
)
from app.models.search_area import GeoPoint


_EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class MissionExecutionSnapshot:
    """
    Estado calculado de una misión en un instante concreto.
    """

    plan: SearchMissionPlan

    position: GeoPoint
    altitude_m: float
    speed_mps: float
    heading_degrees: float

    in_transit: bool

    route_distance_completed_m: float
    route_distance_remaining_m: float


class MissionExecutionEngine:
    """
    Ejecuta virtualmente un plan de búsqueda.

    El motor distingue dos fases:

    1. Tránsito desde la posición inicial del dron hasta
       el primer waypoint.
    2. Recorrido de los waypoints del patrón de búsqueda.

    No mantiene un reloj interno. Recibe el tiempo
    transcurrido para producir un resultado determinista.
    """

    def calculate_snapshot(
        self,
        plan: SearchMissionPlan,
        launch_position: GeoPoint,
        elapsed_seconds: float,
        transit_speed_mps: float,
        search_speed_mps: float,
        time_scale: float = 1.0,
    ) -> MissionExecutionSnapshot:
        """
        Calcula el estado actual del plan.

        elapsed_seconds representa tiempo real.

        time_scale permite acelerar la simulación.
        """

        if elapsed_seconds < 0:
            elapsed_seconds = 0.0

        if transit_speed_mps <= 0:
            transit_speed_mps = 1.0

        if search_speed_mps <= 0:
            search_speed_mps = 1.0

        if time_scale <= 0:
            time_scale = 1.0

        if not plan.waypoints:
            return self._empty_plan_snapshot(
                plan=plan,
                launch_position=launch_position,
            )

        simulated_elapsed_seconds = (
            elapsed_seconds * time_scale
        )

        entry_waypoint = plan.waypoints[0]

        entry_position = GeoPoint(
            latitude=entry_waypoint.latitude,
            longitude=entry_waypoint.longitude,
        )

        transit_distance_m = _calculate_distance_m(
            latitude_1=launch_position.latitude,
            longitude_1=launch_position.longitude,
            latitude_2=entry_position.latitude,
            longitude_2=entry_position.longitude,
        )

        transit_duration_seconds = (
            transit_distance_m
            / transit_speed_mps
        )

        if (
            simulated_elapsed_seconds
            < transit_duration_seconds
        ):
            return self._calculate_transit_snapshot(
                plan=plan,
                launch_position=launch_position,
                entry_position=entry_position,
                transit_distance_m=transit_distance_m,
                simulated_elapsed_seconds=(
                    simulated_elapsed_seconds
                ),
                transit_duration_seconds=(
                    transit_duration_seconds
                ),
                transit_speed_mps=transit_speed_mps,
            )

        search_elapsed_seconds = (
            simulated_elapsed_seconds
            - transit_duration_seconds
        )

        return self._calculate_search_snapshot(
            plan=plan,
            search_elapsed_seconds=(
                search_elapsed_seconds
            ),
            search_speed_mps=search_speed_mps,
        )

    def _calculate_transit_snapshot(
        self,
        plan: SearchMissionPlan,
        launch_position: GeoPoint,
        entry_position: GeoPoint,
        transit_distance_m: float,
        simulated_elapsed_seconds: float,
        transit_duration_seconds: float,
        transit_speed_mps: float,
    ) -> MissionExecutionSnapshot:
        """
        Calcula el desplazamiento hasta el primer waypoint.
        """

        if transit_duration_seconds <= 0:
            progress = 1.0
        else:
            progress = min(
                1.0,
                simulated_elapsed_seconds
                / transit_duration_seconds,
            )

        position = _interpolate_position(
            start=launch_position,
            end=entry_position,
            progress=progress,
        )

        heading = _calculate_heading(
            latitude_1=position.latitude,
            longitude_1=position.longitude,
            latitude_2=entry_position.latitude,
            longitude_2=entry_position.longitude,
        )

        updated_plan = _copy_plan_with_progress(
            plan=plan,
            current_waypoint_index=0,
            coverage_percent=0.0,
            status=MissionPlanStatus.PLANNED,
        )

        return MissionExecutionSnapshot(
            plan=updated_plan,
            position=position,
            altitude_m=plan.altitude_m,
            speed_mps=transit_speed_mps,
            heading_degrees=round(
                heading,
                1,
            ),
            in_transit=True,
            route_distance_completed_m=0.0,
            route_distance_remaining_m=(
                plan.estimated_path_length_m
            ),
        )

    def _calculate_search_snapshot(
        self,
        plan: SearchMissionPlan,
        search_elapsed_seconds: float,
        search_speed_mps: float,
    ) -> MissionExecutionSnapshot:
        """
        Calcula el progreso dentro del patrón de búsqueda.
        """

        total_route_distance_m = (
            _calculate_waypoint_path_length_m(
                plan.waypoints
            )
        )

        if total_route_distance_m <= 0:
            final_waypoint = plan.waypoints[-1]

            final_position = GeoPoint(
                latitude=final_waypoint.latitude,
                longitude=final_waypoint.longitude,
            )

            completed_plan = _copy_plan_with_progress(
                plan=plan,
                current_waypoint_index=(
                    len(plan.waypoints) - 1
                ),
                coverage_percent=100.0,
                status=MissionPlanStatus.COMPLETED,
            )

            return MissionExecutionSnapshot(
                plan=completed_plan,
                position=final_position,
                altitude_m=plan.altitude_m,
                speed_mps=0.0,
                heading_degrees=0.0,
                in_transit=False,
                route_distance_completed_m=0.0,
                route_distance_remaining_m=0.0,
            )

        travelled_route_distance_m = min(
            search_elapsed_seconds
            * search_speed_mps,
            total_route_distance_m,
        )

        completed = (
            travelled_route_distance_m
            >= total_route_distance_m
        )

        coverage_percent = min(
            100.0,
            (
                travelled_route_distance_m
                / total_route_distance_m
            )
            * 100.0,
        )

        (
            position,
            current_waypoint_index,
            heading,
        ) = _position_along_waypoint_path(
            waypoints=plan.waypoints,
            travelled_distance_m=(
                travelled_route_distance_m
            ),
        )

        status = (
            MissionPlanStatus.COMPLETED
            if completed
            else MissionPlanStatus.IN_PROGRESS
        )

        updated_plan = _copy_plan_with_progress(
            plan=plan,
            current_waypoint_index=(
                current_waypoint_index
            ),
            coverage_percent=round(
                coverage_percent,
                1,
            ),
            status=status,
        )

        return MissionExecutionSnapshot(
            plan=updated_plan,
            position=position,
            altitude_m=plan.altitude_m,
            speed_mps=(
                0.0
                if completed
                else search_speed_mps
            ),
            heading_degrees=round(
                heading,
                1,
            ),
            in_transit=False,
            route_distance_completed_m=round(
                travelled_route_distance_m,
                1,
            ),
            route_distance_remaining_m=round(
                max(
                    0.0,
                    total_route_distance_m
                    - travelled_route_distance_m,
                ),
                1,
            ),
        )

    @staticmethod
    def _empty_plan_snapshot(
        plan: SearchMissionPlan,
        launch_position: GeoPoint,
    ) -> MissionExecutionSnapshot:
        """
        Devuelve un estado seguro cuando no existen waypoints.
        """

        updated_plan = _copy_plan_with_progress(
            plan=plan,
            current_waypoint_index=0,
            coverage_percent=0.0,
            status=MissionPlanStatus.PLANNED,
        )

        return MissionExecutionSnapshot(
            plan=updated_plan,
            position=launch_position,
            altitude_m=plan.altitude_m,
            speed_mps=0.0,
            heading_degrees=0.0,
            in_transit=False,
            route_distance_completed_m=0.0,
            route_distance_remaining_m=0.0,
        )


def _copy_plan_with_progress(
    plan: SearchMissionPlan,
    current_waypoint_index: int,
    coverage_percent: float,
    status: MissionPlanStatus,
) -> SearchMissionPlan:
    """
    Crea una copia del plan actualizando únicamente
    sus campos dinámicos.
    """

    plan_data = plan.model_dump()

    plan_data.update(
        {
            "current_waypoint_index": (
                current_waypoint_index
            ),
            "coverage_percent": coverage_percent,
            "status": status,
        }
    )

    return SearchMissionPlan(
        **plan_data
    )


def _position_along_waypoint_path(
    waypoints: list[SearchWaypoint],
    travelled_distance_m: float,
) -> tuple[GeoPoint, int, float]:
    """
    Localiza una posición a una distancia determinada
    dentro de la ruta de waypoints.
    """

    if len(waypoints) == 1:
        waypoint = waypoints[0]

        return (
            GeoPoint(
                latitude=waypoint.latitude,
                longitude=waypoint.longitude,
            ),
            0,
            0.0,
        )

    accumulated_distance_m = 0.0

    for segment_index in range(
        len(waypoints) - 1
    ):
        start_waypoint = waypoints[
            segment_index
        ]

        end_waypoint = waypoints[
            segment_index + 1
        ]

        segment_distance_m = (
            _calculate_distance_m(
                latitude_1=start_waypoint.latitude,
                longitude_1=start_waypoint.longitude,
                latitude_2=end_waypoint.latitude,
                longitude_2=end_waypoint.longitude,
            )
        )

        segment_end_distance_m = (
            accumulated_distance_m
            + segment_distance_m
        )

        if (
            travelled_distance_m
            <= segment_end_distance_m
        ):
            distance_inside_segment_m = max(
                0.0,
                travelled_distance_m
                - accumulated_distance_m,
            )

            if segment_distance_m <= 0:
                segment_progress = 1.0
            else:
                segment_progress = min(
                    1.0,
                    distance_inside_segment_m
                    / segment_distance_m,
                )

            start_position = GeoPoint(
                latitude=start_waypoint.latitude,
                longitude=start_waypoint.longitude,
            )

            end_position = GeoPoint(
                latitude=end_waypoint.latitude,
                longitude=end_waypoint.longitude,
            )

            position = _interpolate_position(
                start=start_position,
                end=end_position,
                progress=segment_progress,
            )

            heading = _calculate_heading(
                latitude_1=start_waypoint.latitude,
                longitude_1=start_waypoint.longitude,
                latitude_2=end_waypoint.latitude,
                longitude_2=end_waypoint.longitude,
            )

            return (
                position,
                segment_index + 1,
                heading,
            )

        accumulated_distance_m = (
            segment_end_distance_m
        )

    final_waypoint = waypoints[-1]

    previous_waypoint = waypoints[-2]

    heading = _calculate_heading(
        latitude_1=previous_waypoint.latitude,
        longitude_1=previous_waypoint.longitude,
        latitude_2=final_waypoint.latitude,
        longitude_2=final_waypoint.longitude,
    )

    return (
        GeoPoint(
            latitude=final_waypoint.latitude,
            longitude=final_waypoint.longitude,
        ),
        len(waypoints) - 1,
        heading,
    )


def _calculate_waypoint_path_length_m(
    waypoints: list[SearchWaypoint],
) -> float:
    """
    Calcula la distancia completa de una ruta.
    """

    total_distance_m = 0.0

    for start_waypoint, end_waypoint in zip(
        waypoints,
        waypoints[1:],
    ):
        total_distance_m += (
            _calculate_distance_m(
                latitude_1=start_waypoint.latitude,
                longitude_1=start_waypoint.longitude,
                latitude_2=end_waypoint.latitude,
                longitude_2=end_waypoint.longitude,
            )
        )

    return total_distance_m


def _interpolate_position(
    start: GeoPoint,
    end: GeoPoint,
    progress: float,
) -> GeoPoint:
    """
    Interpola una posición entre dos coordenadas.
    """

    safe_progress = min(
        1.0,
        max(
            0.0,
            progress,
        ),
    )

    latitude = (
        start.latitude
        + (
            end.latitude
            - start.latitude
        )
        * safe_progress
    )

    longitude = (
        start.longitude
        + (
            end.longitude
            - start.longitude
        )
        * safe_progress
    )

    return GeoPoint(
        latitude=round(
            latitude,
            6,
        ),
        longitude=round(
            longitude,
            6,
        ),
    )


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


def _calculate_heading(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """
    Calcula el rumbo geográfico entre dos posiciones.
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