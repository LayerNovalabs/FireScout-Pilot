from enum import Enum

from pydantic import BaseModel


class EventType(str, Enum):
    FIRE = "fire"
    SMOKE = "smoke"
    VICTIM = "victim"
    GAS = "gas"


class EventSeverity(str, Enum):
    INFORMATION = "information"
    WARNING = "warning"
    CRITICAL = "critical"


class OperationalEvent(BaseModel):
    id: str
    event_type: EventType
    title: str
    description: str
    severity: EventSeverity
    latitude: float
    longitude: float
    confidence: float
    active: bool = True