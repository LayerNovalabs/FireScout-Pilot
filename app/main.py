from fastapi import FastAPI

from app.models.asset import Asset, AssetStatus, AssetType
from app.models.telemetry import Telemetry


app = FastAPI(
    title="FireScout Platform",
    description="Multi-asset emergency intelligence platform",
    version="0.1.0",
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


@app.get("/assets/demo", response_model=Asset)
def get_demo_asset() -> Asset:
    return Asset(
        id="sim-001",
        name="Simulator Alpha",
        asset_type=AssetType.AERIAL_DRONE,
        status=AssetStatus.READY,
        battery=100,
    )


@app.get("/assets", response_model=list[Asset])
def get_assets() -> list[Asset]:
    return [
        Asset(
            id="sim-001",
            name="Simulator Alpha",
            asset_type=AssetType.AERIAL_DRONE,
            status=AssetStatus.ACTIVE,
            battery=92,
            telemetry=Telemetry(
                latitude=41.3874,
                longitude=2.1686,
                altitude=120.0,
                speed=14.5,
                heading=90.0,
            ),
        ),
     Asset(
    id="sim-002",
    name="Simulator Bravo",
    asset_type=AssetType.AERIAL_DRONE,
    status=AssetStatus.ACTIVE,
    battery=84,
    telemetry=Telemetry(
        latitude=41.3920,
        longitude=2.1740,
        altitude=105.0,
        speed=12.8,
        heading=135.0,
    ),
),   
 Asset(
    id="sim-003",
    name="Simulator Charlie",
    asset_type=AssetType.AERIAL_DRONE,
    status=AssetStatus.WARNING,
    battery=28,
    telemetry=Telemetry(
        latitude=41.3825,
        longitude=2.1580,
        altitude=95.0,
        speed=10.2,
        heading=45.0,
    ),
),      
    ]