from dataclasses import dataclass

from app.models.event import EventSeverity, OperationalEvent
from app.models.recommendation import RecommendationPriority


@dataclass
class PriorityEvaluation:
    score: int
    priority: RecommendationPriority
    reason: str


class PriorityEvaluator:
    SEVERITY_SCORES = {
        EventSeverity.INFORMATION: 20,
        EventSeverity.WARNING: 55,
        EventSeverity.CRITICAL: 85,
    }

    def evaluate(
        self,
        event: OperationalEvent,
    ) -> PriorityEvaluation:
        """
        Calculates the operational priority of an event.

        The score is based on:
        - Event severity.
        - Detection confidence.
        - Whether the event is still active.
        """

        severity_score = self.SEVERITY_SCORES[event.severity]

        confidence_score = round(event.confidence * 15)

        active_score = 0

        if event.active:
            active_score = 5

        total_score = min(
            100,
            severity_score
            + confidence_score
            + active_score,
        )

        priority = self._score_to_priority(total_score)

        reason = (
            f"Event severity is {event.severity.value}, "
            f"detection confidence is "
            f"{event.confidence:.0%}, "
            f"and the calculated priority score is "
            f"{total_score}/100."
        )

        return PriorityEvaluation(
            score=total_score,
            priority=priority,
            reason=reason,
        )

    def _score_to_priority(
        self,
        score: int,
    ) -> RecommendationPriority:
        if score >= 85:
            return RecommendationPriority.CRITICAL

        if score >= 65:
            return RecommendationPriority.HIGH

        if score >= 40:
            return RecommendationPriority.MEDIUM

        return RecommendationPriority.LOW