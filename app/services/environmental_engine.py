from app.models.environment import EnvironmentalConditions
from app.services.scenario_manager import ScenarioType


class EnvironmentalEngine:
    """
    Proporciona condiciones ambientales simuladas y deterministas.

    La interfaz queda separada de la fuente de datos para que, en una
    versión profesional, estos valores puedan sustituirse por APIs
    meteorológicas, oceanográficas o modelos de propagación de incendios.
    """

    def get_conditions(
        self,
        scenario: ScenarioType,
    ) -> EnvironmentalConditions:
        if scenario == ScenarioType.MARITIME_SAR:
            return self._get_maritime_conditions()

        return self._get_wildfire_conditions()

    @staticmethod
    def _get_maritime_conditions() -> EnvironmentalConditions:
        return EnvironmentalConditions(
            scenario=ScenarioType.MARITIME_SAR.value,
            source="simulated maritime environmental feed",
            wind_speed_mps=9.2,
            wind_direction_degrees=72.0,
            visibility_km=7.0,
            current_speed_mps=0.65,
            current_direction_degrees=118.0,
            significant_wave_height_m=1.6,
            wave_direction_degrees=86.0,
        )

    @staticmethod
    def _get_wildfire_conditions() -> EnvironmentalConditions:
        return EnvironmentalConditions(
            scenario=ScenarioType.WILDFIRE.value,
            source="simulated wildfire environmental feed",
            wind_speed_mps=7.4,
            wind_direction_degrees=238.0,
            visibility_km=2.8,
            temperature_celsius=34.5,
            smoke_density=0.72,
            slope_percent=18.0,
            slope_direction_degrees=315.0,
        )


def get_active_environment() -> EnvironmentalConditions:
    """
    Devuelve las condiciones ambientales del escenario activo.
    """

    from app.services.scenario_manager import get_active_scenario

    return EnvironmentalEngine().get_conditions(
        get_active_scenario()
    )