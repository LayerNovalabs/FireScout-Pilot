import math

from app.models.environment import EnvironmentalConditions
from app.models.event import EventSeverity, OperationalEvent
from app.models.search_area import GeoPoint, SearchArea
from app.services.environmental_engine import EnvironmentalEngine
from app.services.maritime_events import get_maritime_events
from app.services.scenario_manager import (
    ScenarioType,
    get_active_scenario,
)
from app.services.wildfire_events import get_wildfire_events


_EARTH_RADIUS_M = 6_371_000.0

# Tiempo transcurrido simulado desde la última posición conocida.
_MARITIME_ELAPSED_MINUTES = 18
_WILDFIRE_ELAPSED_MINUTES = 25

# Número de puntos usados para representar la elipse en el mapa.
_ELLIPSE_POINT_COUNT = 48


class SearchAreaEngine:
    """
    Calcula zonas probabilísticas de búsqueda para los incidentes activos.

    En Maritime SAR estima la deriva de la víctima.

    En Wildfire estima una zona de reconocimiento afectada por
    viento, pendiente, humo y propagación del incendio.
    """

    def __init__(
        self,
        environmental_engine: EnvironmentalEngine | None = None,
    ) -> None:
        self._environmental_engine = (
            environmental_engine or EnvironmentalEngine()
        )

    def get_search_areas(
        self,
        scenario: ScenarioType,
    ) -> list[SearchArea]:
        """
        Devuelve las zonas de búsqueda de todos los eventos activos
        correspondientes al escenario indicado.
        """

        environment = self._environmental_engine.get_conditions(
            scenario
        )

        if scenario == ScenarioType.MARITIME_SAR:
            return [
                self.calculate_maritime_area(event, environment)
                for event in get_maritime_events()
                if event.active
            ]

        return [
            self.calculate_wildfire_area(event, environment)
            for event in get_wildfire_events()
            if event.active
        ]

    def calculate_maritime_area(
        self,
        event: OperationalEvent,
        environment: EnvironmentalConditions,
        elapsed_minutes: int = _MARITIME_ELAPSED_MINUTES,
    ) -> SearchArea:
        """
        Calcula la zona probable de una víctima en el mar.

        La deriva se obtiene sumando:

        - corriente superficial;
        - efecto del viento sobre la víctima;
        - deriva inducida por el oleaje.
        """

        current_speed = environment.current_speed_mps or 0.0
        current_direction = (
            environment.current_direction_degrees or 0.0
        )

        wave_height = (
            environment.significant_wave_height_m or 0.0
        )
        wave_direction = (
            environment.wave_direction_degrees or 0.0
        )

        # Vector de la corriente marina.
        current_north, current_east = _vector_components(
            current_speed,
            current_direction,
        )

        # Aproximación inicial: la deriva por viento equivale
        # al 3 % de la velocidad del viento.
        wind_leeway_speed = environment.wind_speed_mps * 0.03

        wind_north, wind_east = _vector_components(
            wind_leeway_speed,
            environment.wind_direction_degrees,
        )

        # Aproximación simplificada del efecto del oleaje.
        wave_drift_speed = wave_height * 0.025

        wave_north, wave_east = _vector_components(
            wave_drift_speed,
            wave_direction,
        )

        # Suma vectorial de todos los factores.
        total_north_mps = (
            current_north
            + wind_north
            + wave_north
        )

        total_east_mps = (
            current_east
            + wind_east
            + wave_east
        )

        effective_speed_mps = math.hypot(
            total_north_mps,
            total_east_mps,
        )

        orientation = _bearing_from_components(
            total_north_mps,
            total_east_mps,
        )

        elapsed_seconds = elapsed_minutes * 60

        north_displacement = (
            total_north_mps * elapsed_seconds
        )

        east_displacement = (
            total_east_mps * elapsed_seconds
        )

        displacement_m = math.hypot(
            north_displacement,
            east_displacement,
        )

        # Centro probable actual de la víctima.
        center = _offset_point(
            event.latitude,
            event.longitude,
            north_displacement,
            east_displacement,
        )

        # La incertidumbre aumenta con el tiempo,
        # el viento y el estado del mar.
        semi_major_axis_m = (
            180.0
            + elapsed_minutes * 18.0
            + wave_height * 90.0
            + environment.wind_speed_mps * 8.0
        )

        semi_minor_axis_m = (
            130.0
            + elapsed_minutes * 12.0
            + wave_height * 70.0
        )

        polygon = _ellipse_polygon(
            center=center,
            semi_major_axis_m=semi_major_axis_m,
            semi_minor_axis_m=semi_minor_axis_m,
            orientation_degrees=orientation,
        )

        return SearchArea(
            id=f"search-area-{event.id}",
            scenario=ScenarioType.MARITIME_SAR.value,
            related_event_id=event.id,
            source_position=GeoPoint(
                latitude=event.latitude,
                longitude=event.longitude,
            ),
            estimated_center=center,
            elapsed_minutes=elapsed_minutes,
            semi_major_axis_m=round(
                semi_major_axis_m,
                1,
            ),
            semi_minor_axis_m=round(
                semi_minor_axis_m,
                1,
            ),
            orientation_degrees=round(
                orientation,
                1,
            ),
            confidence=0.74,
            displacement_m=round(
                displacement_m,
                1,
            ),
            effective_drift_or_spread_mps=round(
                effective_speed_mps,
                3,
            ),
            polygon=polygon,
            environment=environment,
            calculation_summary=(
                "Estimated from the vector sum of surface "
                "current, 3% wind leeway and wave-induced "
                "drift. The ellipse expands with elapsed "
                "time, wind and sea state."
            ),
        )

    def calculate_wildfire_area(
        self,
        event: OperationalEvent,
        environment: EnvironmentalConditions,
        elapsed_minutes: int = _WILDFIRE_ELAPSED_MINUTES,
    ) -> SearchArea:
        """
        Calcula una zona de reconocimiento para Wildfire.

        La orientación se obtiene combinando:

        - dirección del viento;
        - dirección ascendente de la pendiente.

        El tamaño aumenta según:

        - velocidad estimada de propagación;
        - densidad de humo;
        - gravedad del incidente.
        """

        smoke_density = environment.smoke_density or 0.0
        slope_percent = environment.slope_percent or 0.0
        slope_direction = (
            environment.slope_direction_degrees or 0.0
        )

        wind_weight = max(
            environment.wind_speed_mps,
            0.1,
        )

        slope_weight = max(
            slope_percent / 5.0,
            0.1,
        )

        wind_north, wind_east = _vector_components(
            wind_weight,
            environment.wind_direction_degrees,
        )

        slope_north, slope_east = _vector_components(
            slope_weight,
            slope_direction,
        )

        combined_north = wind_north + slope_north
        combined_east = wind_east + slope_east

        orientation = _bearing_from_components(
            combined_north,
            combined_east,
        )

        # Modelo inicial y simplificado de propagación.
        spread_speed_mps = (
            0.04
            + environment.wind_speed_mps * 0.020
            + slope_percent * 0.0025
        )

        elapsed_seconds = elapsed_minutes * 60
        spread_distance_m = (
            spread_speed_mps * elapsed_seconds
        )

        # El centro se desplaza parcialmente en la dirección
        # probable de propagación.
        center_offset_m = spread_distance_m * 0.35

        center_north, center_east = _vector_components(
            center_offset_m,
            orientation,
        )

        center = _offset_point(
            event.latitude,
            event.longitude,
            center_north,
            center_east,
        )

        base_radius_by_severity = {
            EventSeverity.CRITICAL: 420.0,
            EventSeverity.WARNING: 320.0,
            EventSeverity.INFORMATION: 240.0,
        }

        base_radius = base_radius_by_severity[
            event.severity
        ]

        semi_major_axis_m = (
            base_radius
            + spread_distance_m * 0.90
            + smoke_density * 140.0
        )

        semi_minor_axis_m = (
            base_radius * 0.65
            + environment.wind_speed_mps * 12.0
            + smoke_density * 90.0
        )

        # El humo reduce la confianza de la estimación.
        confidence = max(
            0.45,
            min(
                0.90,
                event.confidence
                * (0.90 - smoke_density * 0.22),
            ),
        )

        polygon = _ellipse_polygon(
            center=center,
            semi_major_axis_m=semi_major_axis_m,
            semi_minor_axis_m=semi_minor_axis_m,
            orientation_degrees=orientation,
        )

        return SearchArea(
            id=f"search-area-{event.id}",
            scenario=ScenarioType.WILDFIRE.value,
            related_event_id=event.id,
            source_position=GeoPoint(
                latitude=event.latitude,
                longitude=event.longitude,
            ),
            estimated_center=center,
            elapsed_minutes=elapsed_minutes,
            semi_major_axis_m=round(
                semi_major_axis_m,
                1,
            ),
            semi_minor_axis_m=round(
                semi_minor_axis_m,
                1,
            ),
            orientation_degrees=round(
                orientation,
                1,
            ),
            confidence=round(
                confidence,
                2,
            ),
            displacement_m=round(
                center_offset_m,
                1,
            ),
            effective_drift_or_spread_mps=round(
                spread_speed_mps,
                3,
            ),
            polygon=polygon,
            environment=environment,
            calculation_summary=(
                "Reconnaissance ellipse projected from the "
                "reported fire position using wind, upslope "
                "tendency, estimated spread, smoke density "
                "and incident severity."
            ),
        )


def get_active_search_areas() -> list[SearchArea]:
    """
    Devuelve las zonas de búsqueda del escenario activo.
    """

    return SearchAreaEngine().get_search_areas(
        get_active_scenario()
    )


def _vector_components(
    magnitude: float,
    bearing_degrees: float,
) -> tuple[float, float]:
    """
    Convierte una magnitud y un rumbo en componentes
    norte y este.
    """

    bearing_radians = math.radians(
        bearing_degrees
    )

    north = magnitude * math.cos(
        bearing_radians
    )

    east = magnitude * math.sin(
        bearing_radians
    )

    return north, east


def _bearing_from_components(
    north: float,
    east: float,
) -> float:
    """
    Convierte las componentes norte y este en un rumbo
    entre 0 y 360 grados.
    """

    if (
        math.isclose(north, 0.0)
        and math.isclose(east, 0.0)
    ):
        return 0.0

    return (
        math.degrees(
            math.atan2(east, north)
        )
        + 360.0
    ) % 360.0


def _offset_point(
    latitude: float,
    longitude: float,
    north_m: float,
    east_m: float,
) -> GeoPoint:
    """
    Desplaza una coordenada una determinada distancia
    hacia el norte y hacia el este.
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


def _ellipse_polygon(
    center: GeoPoint,
    semi_major_axis_m: float,
    semi_minor_axis_m: float,
    orientation_degrees: float,
) -> list[GeoPoint]:
    """
    Genera los puntos geográficos necesarios para dibujar
    una elipse en Leaflet.
    """

    polygon: list[GeoPoint] = []

    for index in range(_ELLIPSE_POINT_COUNT):
        angle = (
            2.0
            * math.pi
            * index
            / _ELLIPSE_POINT_COUNT
        )

        major_component = (
            semi_major_axis_m
            * math.cos(angle)
        )

        minor_component = (
            semi_minor_axis_m
            * math.sin(angle)
        )

        major_north, major_east = (
            _vector_components(
                major_component,
                orientation_degrees,
            )
        )

        minor_north, minor_east = (
            _vector_components(
                minor_component,
                orientation_degrees + 90.0,
            )
        )

        polygon.append(
            _offset_point(
                center.latitude,
                center.longitude,
                major_north + minor_north,
                major_east + minor_east,
            )
        )

    return polygon