from enum import Enum

from pydantic import BaseModel, Field


class DetectionStatus(str, Enum):
    """
    Nivel de confirmación de una detección.
    """

    POSSIBLE = "possible"
    CONFIRMED = "confirmed"


class DetectionTargetType(str, Enum):
    """
    Tipos de objetivos que pueden detectar
    los sensores de FireScout.
    """

    PERSON = "person"


class SensorType(str, Enum):
    """
    Sensores disponibles en los drones.
    """

    THERMAL_CAMERA = "thermal_camera"
    MULTISPECTRAL_CAMERA = "multispectral_camera"


class SensorDetection(BaseModel):
    """
    Detección visible para el operador.

    La posición real de la víctima nunca se expone
    hasta que el sistema produce una detección.
    """

    id: str
    scenario: str

    related_event_id: str

    source_asset_id: str
    source_asset_name: str

    target_type: DetectionTargetType
    sensor_type: SensorType

    status: DetectionStatus

    latitude: float = Field(
        ge=-90,
        le=90,
    )

    longitude: float = Field(
        ge=-180,
        le=180,
    )

    confidence_percent: float = Field(
        ge=0,
        le=100,
    )

    detection_radius_m: float = Field(
        gt=0,
    )

    distance_to_target_m: float = Field(
        ge=0,
    )

    environment_factor: float = Field(
        ge=0,
        le=1,
    )

    first_detected_at_seconds: float = Field(
        ge=0,
    )

    last_updated_at_seconds: float = Field(
        ge=0,
    )

    message: str


class SensorMissionStatus(BaseModel):
    """
    Estado del sensor asociado a una misión,
    aunque todavía no exista una detección.
    """

    mission_plan_id: str
    scenario: str

    related_event_id: str

    asset_id: str
    asset_name: str

    sensor_type: SensorType

    sensor_active: bool

    detection_radius_m: float = Field(
        gt=0,
    )

    environment_factor: float = Field(
        ge=0,
        le=1,
    )

    nearest_target_distance_m: float | None = Field(
        default=None,
        ge=0,
    )

    detection_status: DetectionStatus | None = None

    message: str