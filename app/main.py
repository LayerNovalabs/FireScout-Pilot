from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models.asset import Asset, AssetStatus, AssetType
from app.models.environment import EnvironmentalConditions
from app.models.event import OperationalEvent
from app.models.mission_plan import SearchMissionPlan
from app.models.recommendation import OperationalRecommendation
from app.models.search_area import SearchArea

from app.services.decision_engine import (
    get_operational_recommendations,
)
from app.services.environmental_engine import (
    get_active_environment,
)
from app.services.maritime_decision_engine import (
    get_maritime_recommendations,
)
from app.services.maritime_events import (
    get_maritime_events,
)
from app.services.maritime_simulator import (
    get_maritime_assets,
    reset_maritime_simulation,
)
from app.services.mission_runtime import (
    get_active_executed_mission_plans,
    reset_mission_execution,
)
from app.services.scenario_manager import (
    ScenarioType,
    get_active_scenario,
    set_active_scenario,
)
from app.services.search_area_engine import (
    get_active_search_areas,
)
from app.services.simulator import (
    get_simulated_assets,
)
from app.services.wildfire_events import (
    get_wildfire_events,
)


app = FastAPI(
    title="FireScout Platform",
    description=(
        "Multi-asset emergency intelligence platform"
    ),
    version="0.1.0",
)


app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)


templates = Jinja2Templates(
    directory="app/templates",
)


def _get_active_assets() -> list[Asset]:
    """
    Devuelve los activos correspondientes
    al escenario actualmente seleccionado.
    """

    scenario = get_active_scenario()

    if scenario == ScenarioType.MARITIME_SAR:
        return get_maritime_assets()

    return get_simulated_assets()


def _get_active_events() -> list[OperationalEvent]:
    """
    Devuelve los eventos correspondientes
    al escenario actualmente seleccionado.
    """

    scenario = get_active_scenario()

    if scenario == ScenarioType.MARITIME_SAR:
        return get_maritime_events()

    return get_wildfire_events()


def _get_active_recommendations(
) -> list[OperationalRecommendation]:
    """
    Devuelve las recomendaciones operacionales
    del escenario actualmente seleccionado.
    """

    scenario = get_active_scenario()

    if scenario == ScenarioType.MARITIME_SAR:
        return get_maritime_recommendations()

    return get_operational_recommendations()


@app.get("/")
def home() -> dict[str, str]:
    """
    Información básica de la plataforma.
    """

    return {
        "name": "FireScout Platform",
        "status": "running",
        "version": "0.1.0",
        "active_scenario": (
            get_active_scenario().value
        ),
    }


@app.get("/health")
def health() -> dict[str, str]:
    """
    Estado de salud del backend.
    """

    return {
        "status": "healthy",
    }


@app.get("/scenarios")
def get_scenarios() -> dict[str, object]:
    """
    Devuelve los escenarios disponibles
    y el escenario activo.
    """

    return {
        "active": get_active_scenario().value,
        "available": [
            ScenarioType.WILDFIRE.value,
            ScenarioType.MARITIME_SAR.value,
        ],
    }


@app.get("/scenario")
def get_scenario() -> dict[str, str]:
    """
    Devuelve el escenario actualmente seleccionado.
    """

    return {
        "active": get_active_scenario().value,
    }


@app.post("/scenario/{scenario}")
def select_scenario(
    scenario: ScenarioType,
) -> dict[str, str]:
    """
    Cambia el escenario activo y reinicia
    sus simulaciones y planes de misión.
    """

    selected_scenario = set_active_scenario(
        scenario
    )

    reset_mission_execution(
        selected_scenario
    )

    if selected_scenario == ScenarioType.MARITIME_SAR:
        reset_maritime_simulation()

    return {
        "active": selected_scenario.value,
        "message": "Scenario changed successfully",
    }


@app.get(
    "/command-center",
    response_class=HTMLResponse,
)
def command_center(
    request: Request,
):
    """
    Muestra el Command Center.
    """

    assets = _get_active_assets()

    return templates.TemplateResponse(
        request=request,
        name="command_center.html",
        context={
            "assets": assets,
            "active_scenario": (
                get_active_scenario().value
            ),
        },
    )


@app.get(
    "/assets/demo",
    response_model=Asset,
)
def get_demo_asset() -> Asset:
    """
    Devuelve un activo de demostración.
    """

    return Asset(
        id="sim-001",
        name="Simulator Alpha",
        asset_type=AssetType.AERIAL_DRONE,
        status=AssetStatus.READY,
        battery=100,
    )


@app.get(
    "/assets",
    response_model=list[Asset],
)
def get_assets() -> list[Asset]:
    """
    Devuelve los activos del escenario activo.
    """

    return _get_active_assets()


@app.get(
    "/events",
    response_model=list[OperationalEvent],
)
def get_events() -> list[OperationalEvent]:
    """
    Devuelve los eventos del escenario activo.
    """

    return _get_active_events()


@app.get(
    "/recommendations",
    response_model=list[OperationalRecommendation],
)
def get_recommendations(
) -> list[OperationalRecommendation]:
    """
    Devuelve las recomendaciones del Decision Engine.
    """

    return _get_active_recommendations()


@app.get(
    "/environment",
    response_model=EnvironmentalConditions,
)
def get_environment() -> EnvironmentalConditions:
    """
    Devuelve las condiciones ambientales utilizadas
    para calcular la zona de búsqueda.
    """

    return get_active_environment()


@app.get(
    "/search-areas",
    response_model=list[SearchArea],
)
def get_search_areas() -> list[SearchArea]:
    """
    Devuelve todas las zonas de búsqueda calculadas
    para el escenario activo.
    """

    return get_active_search_areas()


@app.get(
    "/search-area",
    response_model=SearchArea | None,
)
def get_primary_search_area() -> SearchArea | None:
    """
    Devuelve la primera zona de búsqueda activa.
    """

    search_areas = get_active_search_areas()

    if not search_areas:
        return None

    return search_areas[0]


@app.get(
    "/mission-plans",
    response_model=list[SearchMissionPlan],
)
def get_mission_plans() -> list[SearchMissionPlan]:
    """
    Devuelve los planes de búsqueda con progreso dinámico.
    """

    return get_active_executed_mission_plans()


@app.get(
    "/mission-plan",
    response_model=SearchMissionPlan | None,
)
def get_primary_mission_plan(
) -> SearchMissionPlan | None:
    """
    Devuelve el plan principal con progreso dinámico.
    """

    mission_plans = (
        get_active_executed_mission_plans()
    )

    if not mission_plans:
        return None

    return mission_plans[0]


@app.post("/mission/reset")
def reset_active_mission() -> dict[str, str]:
    """
    Reinicia manualmente el progreso de la misión activa.
    """

    scenario = get_active_scenario()

    reset_mission_execution(
        scenario
    )

    if scenario == ScenarioType.MARITIME_SAR:
        reset_maritime_simulation()

    return {
        "status": "reset",
        "scenario": scenario.value,
    }