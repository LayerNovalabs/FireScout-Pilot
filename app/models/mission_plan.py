from enum import Enum

from pydantic import BaseModel, Field

from app.models.search_area import GeoPoint


class SearchPattern(str, Enum):
    """
    Patrones de búsqueda soportados por FireScout.
    """

    PARALLEL_TRACK = "parallel_track"


class MissionPlanStatus(str, Enum):
    """
    Estado actual del plan de búsqueda.
    """

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class SearchWaypoint(BaseModel):
    """
    Punto individual que debe recorrer el dron.
    """

    sequence: int = Field(ge=0)

    latitude: float = Field(
        ge=-90,
        le=90,
    )

    longitude: float = Field(
        ge=-180,
        le=180,
    )

    altitude_m: float = Field(
        gt=0,
    )

    action: str = "search"


class SearchMissionPlan(BaseModel):
    """
    Plan automático de cobertura de una zona de búsqueda.
    """

    id: str
    scenario: str

    related_event_id: str
    search_area_id: str

    # Dron asignado exclusivamente a este plan.
    assigned_asset_id: str
    assigned_asset_name: str

    pattern: SearchPattern

    orientation_degrees: float = Field(
        ge=0,
        lt=360,
    )

    track_spacing_m: float = Field(
        gt=0,
    )

    altitude_m: float = Field(
        gt=0,
    )

    entry_point: GeoPoint

    waypoints: list[SearchWaypoint]

    waypoint_count: int = Field(
        ge=0,
    )

    estimated_path_length_m: float = Field(
        ge=0,
    )

    estimated_duration_minutes: float = Field(
        ge=0,
    )

    current_waypoint_index: int = Field(
        ge=0,
    )

    coverage_percent: float = Field(
        ge=0,
        le=100,
    )

    status: MissionPlanStatus

    calculation_summary: str