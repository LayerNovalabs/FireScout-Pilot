from pydantic import BaseModel


class Telemetry(BaseModel):
    latitude: float
    longitude: float
    altitude: float
    speed: float
    heading: float