from fastapi import (
    FastAPI,
    HTTPException,
    Request,
)
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models.asset import (
    Asset,
    AssetStatus,
    AssetType,
)
from app.models.detection import (
    SensorDetection,
    SensorMissionStatus,
)
from app.models.environment import (
    EnvironmentalConditions,
)
from app.models.event import OperationalEvent
from app.models.mission_plan import (
    SearchMissionPlan,
)
from app.models.operational_log import (
    OperationalTimeline,
)
from app.models.pilot_telemetry import (
    PilotTelemetry,
)
from app.models.recommendation import (
    OperationalRecommendation,
)
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
from app.services.mission_control import (
    clear_all_missions,
)
from app.services.mission_runtime import (
    get_active_executed_mission_plans,
    reset_mission_execution,
)
from app.services.operational_log_service import (
    get_active_operational_timeline,
    record_scenario_change,
    reset_operational_log,
)
from app.services.pilot_telemetry_service import (
    get_all_pilot_telemetry,
    get_pilot_telemetry,
    get_pilot_telemetry_history,
    save_pilot_telemetry,
)
from app.services.scenario_manager import (
    ScenarioType,
    get_active_scenario,
    set_active_scenario,
)
from app.services.search_area_engine import (
    get_active_search_areas,
)
from app.services.sensor_detection_engine import (
    get_active_detections,
    get_active_sensor_statuses,
    reset_sensor_detections,
)
from app.services.simulator import (
    get_simulated_assets,
    reset_wildfire_simulation,
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
    StaticFiles(
        directory="app/static",
    ),
    name="static",
)


templates = Jinja2Templates(
    directory="app/templates",
)


def _get_active_assets() -> list[Asset]:
    """
    Devuelve los activos del escenario activo.
    """

    scenario = get_active_scenario()

    if scenario == ScenarioType.MARITIME_SAR:
        return get_maritime_assets()

    return get_simulated_assets()


def _get_active_events(
) -> list[OperationalEvent]:
    """
    Devuelve los eventos del escenario activo.
    """

    scenario = get_active_scenario()

    if scenario == ScenarioType.MARITIME_SAR:
        return get_maritime_events()

    return get_wildfire_events()


def _get_active_recommendations(
) -> list[OperationalRecommendation]:
    """
    Devuelve las recomendaciones operativas
    del escenario activo.
    """

    scenario = get_active_scenario()

    if scenario == ScenarioType.MARITIME_SAR:
        return get_maritime_recommendations()

    return get_operational_recommendations()


@app.get(
    "/",
    include_in_schema=False,
)
def home() -> RedirectResponse:
    """
    Abre directamente el Command Center.
    """

    return RedirectResponse(
        url="/command-center",
        status_code=302,
    )
@app.get(
    "/pilot-center",
    response_class=HTMLResponse,
)
def pilot_center(
    request: Request,
):
    """
    Muestra el panel de telemetría
    de los drones piloto.
    """

    return templates.TemplateResponse(
        request=request,
        name="pilot_center.html",
        context={},
    )


@app.get("/health")
def health() -> dict[str, str]:
    """
    Comprueba que la aplicación funciona.
    """

    return {
        "status": "healthy",
    }


@app.get("/scenarios")
def get_scenarios() -> dict[str, object]:
    """
    Devuelve los escenarios disponibles.
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
    Devuelve el escenario activo.
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
    sus simulaciones dinámicas.
    """

    selected_scenario = set_active_scenario(
        scenario
    )

    reset_mission_execution()
    reset_sensor_detections()

    if (
        selected_scenario
        == ScenarioType.MARITIME_SAR
    ):
        reset_maritime_simulation()

    record_scenario_change(
        selected_scenario
    )

    return {
        "active": selected_scenario.value,
        "message": (
            "Scenario changed successfully"
        ),
    }


@app.get(
    "/command-center",
    response_class=HTMLResponse,
)
def command_center(
    request: Request,
):
    """
    Muestra el centro de mando de FireScout.
    """

    reset_mission()

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
    Devuelve los eventos operativos activos.
    """

    return _get_active_events()


@app.get(
    "/recommendations",
    response_model=list[
        OperationalRecommendation
    ],
)
def get_recommendations(
) -> list[OperationalRecommendation]:
    """
    Devuelve las recomendaciones del
    Decision Engine.
    """

    return _get_active_recommendations()


@app.get(
    "/environment",
    response_model=EnvironmentalConditions,
)
def get_environment(
) -> EnvironmentalConditions:
    """
    Devuelve las condiciones ambientales
    del escenario activo.
    """

    return get_active_environment()


@app.get(
    "/search-areas",
    response_model=list[SearchArea],
)
def get_search_areas() -> list[SearchArea]:
    """
    Devuelve todas las áreas de búsqueda.
    """

    return get_active_search_areas()


@app.get(
    "/search-area",
    response_model=SearchArea,
)
def get_primary_search_area() -> SearchArea:
    """
    Devuelve el área de búsqueda principal.
    """

    search_areas = get_active_search_areas()

    return search_areas[0]


@app.get(
    "/mission-plans",
    response_model=list[SearchMissionPlan],
)
def get_mission_plans(
) -> list[SearchMissionPlan]:
    """
    Devuelve todos los planes dinámicos del
    escenario activo.
    """

    return (
        get_active_executed_mission_plans()
    )


@app.get(
    "/mission-plan",
    response_model=SearchMissionPlan,
)
def get_primary_mission_plan(
) -> SearchMissionPlan:
    """
    Devuelve el primer plan de misión activo.
    """

    mission_plans = (
        get_active_executed_mission_plans()
    )

    return mission_plans[0]


@app.post("/mission/reset")
def reset_mission() -> dict[str, str]:
    """
    Reinicia misiones, sensores, baterías
    e historial del escenario activo.
    """

    active_scenario = get_active_scenario()

    reset_mission_execution()
    reset_sensor_detections()
    reset_operational_log(
        active_scenario
    )
    clear_all_missions()

    if (
        active_scenario
        == ScenarioType.MARITIME_SAR
    ):
        reset_maritime_simulation()
    else:
        reset_wildfire_simulation()

    return {
        "status": "reset",
        "message": (
            "Mission, sensors, batteries and "
            "operational timeline reset successfully"
        ),
    }


@app.get(
    "/detections",
    response_model=list[SensorDetection],
)
def get_detections(
) -> list[SensorDetection]:
    """
    Devuelve las detecciones visibles
    del escenario activo.
    """

    return get_active_detections()


@app.get(
    "/sensor-statuses",
    response_model=list[SensorMissionStatus],
)
def get_sensor_statuses(
) -> list[SensorMissionStatus]:
    """
    Devuelve el estado operativo de los sensores,
    incluso cuando todavía no existe una detección.
    """

    return get_active_sensor_statuses()


@app.get(
    "/operational-timeline",
    response_model=OperationalTimeline,
)
def get_operational_timeline(
) -> OperationalTimeline:
    """
    Devuelve la cronología operativa completa
    del escenario activo.
    """

    return get_active_operational_timeline()


@app.post(
    "/api/drones/telemetry",
    response_model=PilotTelemetry,
    status_code=201,
)
def receive_pilot_telemetry(
    telemetry: PilotTelemetry,
) -> PilotTelemetry:
    """
    Recibe y guarda la última telemetría
    enviada por un dron piloto.
    """

    return save_pilot_telemetry(
        telemetry
    )


@app.get(
    "/api/drones",
    response_model=list[PilotTelemetry],
)
def get_pilot_drones(
) -> list[PilotTelemetry]:
    """
    Devuelve la última telemetría conocida
    de todos los drones piloto.
    """

    return get_all_pilot_telemetry()


@app.get(
    "/api/drones/{drone_id}",
    response_model=PilotTelemetry,
)
def get_pilot_drone(
    drone_id: str,
) -> PilotTelemetry:
    """
    Devuelve la última telemetría conocida
    de un dron piloto concreto.
    """

    telemetry = get_pilot_telemetry(
        drone_id
    )

    if telemetry is None:
        raise HTTPException(
            status_code=404,
            detail="Drone telemetry not found",
        )

    return telemetry
@app.get(
    "/api/drones/{drone_id}/history",
    response_model=list[PilotTelemetry],
)
def get_pilot_drone_history(
    drone_id: str,
) -> list[PilotTelemetry]:
    """
    Devuelve el historial reciente
    de telemetría de un dron piloto.
    """

    telemetry = get_pilot_telemetry(
        drone_id
    )

    if telemetry is None:
        raise HTTPException(
            status_code=404,
            detail="Drone telemetry not found",
        )

    return get_pilot_telemetry_history(
        drone_id
    )