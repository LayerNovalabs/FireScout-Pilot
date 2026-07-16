from pydantic import BaseModel, Field


class EnvironmentalConditions(BaseModel):
    """
    Condiciones ambientales utilizadas para calcular
    las zonas de búsqueda de FireScout.
    """

    scenario: str
    source: str = "simulated"

    # Condiciones generales
    wind_speed_mps: float = Field(ge=0)
    wind_direction_degrees: float = Field(ge=0, lt=360)
    visibility_km: float = Field(ge=0)

    # Condiciones marítimas
    current_speed_mps: float | None = Field(
        default=None,
        ge=0,
    )
    current_direction_degrees: float | None = Field(
        default=None,
        ge=0,
        lt=360,
    )
    significant_wave_height_m: float | None = Field(
        default=None,
        ge=0,
    )
    wave_direction_degrees: float | None = Field(
        default=None,
        ge=0,
        lt=360,
    )

    # Condiciones de incendio forestal
    temperature_celsius: float | None = None
    smoke_density: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )
    slope_percent: float | None = Field(
        default=None,
        ge=0,
    )
    slope_direction_degrees: float | None = Field(
        default=None,
        ge=0,
        lt=360,
    )

    direction_convention: str = (
        "All bearings indicate the direction towards which "
        "the environmental vector moves."
    )