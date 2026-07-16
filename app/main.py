from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models.asset import Asset, AssetStatus, AssetType
from app.models.environment import EnvironmentalConditions
from app.models.event import OperationalEvent
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
    description="Multi-asset emergency intelligence platform",
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
    return {
        "name": "FireScout Platform",
        "status": "running",
        "version": "0.1.0",
        "active_scenario": get_active_scenario().value,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "healthy",
    }


@app.get("/scenarios")
def get_scenarios() -> dict[str, object]:
    return {
        "active": get_active_scenario().value,
        "available": [
            ScenarioType.WILDFIRE.value,
            ScenarioType.MARITIME_SAR.value,
        ],
    }


@app.get("/scenario")
def get_scenario() -> dict[str, str]:
    return {
        "active": get_active_scenario().value,
    }


@app.post("/scenario/{scenario}")
def select_scenario(
    scenario: ScenarioType,
) -> dict[str, str]:
    selected_scenario = set_active_scenario(
        scenario
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
    return _get_active_assets()


@app.get(
    "/events",
    response_model=list[OperationalEvent],
)
def get_events() -> list[OperationalEvent]:
    return _get_active_events()


@app.get(
    "/recommendations",
    response_model=list[OperationalRecommendation],
)
def get_recommendations(
) -> list[OperationalRecommendation]:
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
    para los eventos activos del escenario actual.
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