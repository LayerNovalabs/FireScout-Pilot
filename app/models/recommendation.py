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