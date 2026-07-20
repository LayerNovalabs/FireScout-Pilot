from enum import Enum

from pydantic import BaseModel, Field


class OperationalLogType(str, Enum):
    """
    Categoría del acontecimiento registrado.
    """

    SYSTEM = "system"
    SCENARIO = "scenario"
    EVENT = "event"
    ASSIGNMENT = "assignment"
    MISSION = "mission"
    SENSOR = "sensor"
    DETECTION = "detection"
    RESCUE = "rescue"


class OperationalLogSeverity(str, Enum):
    """
    Importancia visual y operativa del registro.
    """

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    CRITICAL = "critical"


class OperationalLogEntry(BaseModel):
    """
    Entrada individual del historial operativo.
    """

    id: str

    scenario: str

    entry_type: OperationalLogType
    severity: OperationalLogSeverity

    title: str
    message: str

    related_event_id: str | None = None

    asset_id: str | None = None
    asset_name: str | None = None

    mission_status: str | None = None

    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
    )

    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
    )

    timestamp_seconds: float = Field(
        ge=0,
    )

    timestamp_iso: str


class OperationalTimeline(BaseModel):
    """
    Cronología completa del escenario activo.
    """

    scenario: str

    generated_at_iso: str

    total_entries: int = Field(
        ge=0,
    )

    entries: list[OperationalLogEntry]