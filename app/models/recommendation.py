from enum import Enum

from pydantic import BaseModel


class RecommendationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OperationalRecommendation(BaseModel):
    id: str
    title: str
    action: str
    reason: str
    priority: RecommendationPriority
    related_event_id: str
    estimated_response_minutes: int

    assigned_asset_name: str | None = None
    priority_score: int | None = None
    distance_km: float | None = None

