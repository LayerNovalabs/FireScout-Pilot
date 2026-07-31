from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class PilotTelemetry(BaseModel):
    """
    Telemetría recibida desde un dron real,
    una aplicación puente o un simulador externo.
    """

    drone_id: str = Field(
        min_length=1,
        max_length=100,
    )

    latitude: float = Field(
        ge=-90.0,
        le=90.0,
    )

    longitude: float = Field(
        ge=-180.0,
        le=180.0,
    )

    altitude_m: float = Field(
        ge=0.0,
    )

    speed_mps: float = Field(
        ge=0.0,
    )

    heading_degrees: float = Field(
        ge=0.0,
        lt=360.0,
    )

    battery_percent: int = Field(
        ge=0,
        le=100,
    )

    flight_status: Literal[
        "offline",
        "ready",
        "flying",
        "landing",
        "returning_home",
        "error",
    ]

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )