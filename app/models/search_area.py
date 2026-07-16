from enum import Enum

from pydantic import BaseModel, Field

from app.models.environment import EnvironmentalConditions


class SearchAreaShape(str, Enum):
    ELLIPSE = "ellipse"


class GeoPoint(BaseModel):
    """
    Punto geográfico expresado en latitud y longitud.
    """

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class SearchArea(BaseModel):
    """
    Zona probable de búsqueda calculada por FireScout.
    """

    id: str
    scenario: str
    related_event_id: str

    shape: SearchAreaShape = SearchAreaShape.ELLIPSE

    # Posición desde la que parte el cálculo.
    source_position: GeoPoint

    # Centro estimado de la zona probable.
    estimated_center: GeoPoint

    elapsed_minutes: int = Field(ge=0)

    # Dimensiones de la elipse.
    semi_major_axis_m: float = Field(gt=0)
    semi_minor_axis_m: float = Field(gt=0)

    # Orientación del eje principal.
    orientation_degrees: float = Field(ge=0, lt=360)

    # Confianza estimada del área calculada.
    confidence: float = Field(ge=0, le=1)

    # Datos derivados del cálculo.
    displacement_m: float = Field(ge=0)
    effective_drift_or_spread_mps: float = Field(ge=0)

    # Puntos utilizados para dibujar la zona en el mapa.
    polygon: list[GeoPoint]

    # Condiciones ambientales utilizadas.
    environment: EnvironmentalConditions

    # Explicación legible del cálculo.
    calculation_summary: str