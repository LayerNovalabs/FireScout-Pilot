from enum import Enum


class ScenarioType(str, Enum):
    WILDFIRE = "wildfire"
    MARITIME_SAR = "maritime_sar"


_active_scenario = ScenarioType.WILDFIRE


def get_active_scenario() -> ScenarioType:
    return _active_scenario


def set_active_scenario(
    scenario: ScenarioType,
) -> ScenarioType:
    global _active_scenario

    _active_scenario = scenario

    return _active_scenario