from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models.asset import Asset, AssetStatus, AssetType
from app.models.event import OperationalEvent
from app.models.recommendation import OperationalRecommendation
from app.services.decision_engine import get_operational_recommendations
from app.services.simulator import get_simulated_assets
from app.services.wildfire_events import get_wildfire_events


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
    directory="app/templates"
)


@app.get("/")
def home() -> dict[str, str]:
    return {
        "name": "FireScout Platform",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "healthy",
    }


@app.get(
    "/command-center",
    response_class=HTMLResponse,
)
def command_center(request: Request):
    assets = get_simulated_assets()

    return templates.TemplateResponse(
        request=request,
        name="command_center.html",
        context={
            "assets": assets,
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
    return get_simulated_assets()


@app.get(
    "/events",
    response_model=list[OperationalEvent],
)
def get_events() -> list[OperationalEvent]:
    return get_wildfire_events()


@app.get(
    "/recommendations",
    response_model=list[OperationalRecommendation],
)
def get_recommendations() -> list[OperationalRecommendation]:
    return get_operational_recommendations()