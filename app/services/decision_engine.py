from app.models.recommendation import (
    OperationalRecommendation,
    RecommendationPriority,
)


def get_operational_recommendations(
) -> list[OperationalRecommendation]:
    return [
        OperationalRecommendation(
            id="recommendation-001",
            title="Deploy response team",
            action=(
                "Dispatch the nearest ground response team "
                "to the detected fire zone."
            ),
            reason=(
                "A critical fire event was detected with "
                "97% confidence."
            ),
            priority=RecommendationPriority.CRITICAL,
            related_event_id="event-001",
            estimated_response_minutes=4,
        )
    ]
