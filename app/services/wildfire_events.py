from app.models.event import (
    EventSeverity,
    EventType,
    OperationalEvent,
)


def get_wildfire_events() -> list[OperationalEvent]:
    return [
        OperationalEvent(
            id="event-001",
            event_type=EventType.FIRE,
            title="Active fire detected",
            description=(
                "High-temperature zone detected by Simulator Alpha."
            ),
            severity=EventSeverity.CRITICAL,
            latitude=41.3885,
            longitude=2.1705,
            confidence=0.97,
            active=True,
        )
    ]