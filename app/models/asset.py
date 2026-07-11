from enum import Enum

from pydantic import BaseModel

from app.models.telemetry import Telemetry


class AssetType(str, Enum):
    AERIAL_DRONE = "aerial_drone"
    GROUND_ROBOT = "ground_robot"
    MARITIME_VEHICLE = "maritime_vehicle"
    FIXED_SENSOR = "fixed_sensor"


class AssetStatus(str, Enum):
    OFFLINE = "offline"
    READY = "ready"
    ACTIVE = "active"
    WARNING = "warning"


class Asset(BaseModel):
    id: str
    name: str
    asset_type: AssetType
    status: AssetStatus
    battery: int | None = None
    telemetry: Telemetry | None = None