from app.models.event import (
    EventSeverity,
    EventType,
    OperationalEvent,
)

def get_maritime_events() -> list[OperationalEvent]:
    return [
        OperationalEvent(
            id="sar-event-001",
            event_type=EventType.VICTIM,
            title="Person overboard detected",
            description=(
                "Thermal signature and flotation device detected "
                "in the maritime search area."
            ),
            severity=EventSeverity.CRITICAL,
            latitude=41.3475,
            longitude=2.2470,
            confidence=0.94,
            active=True,
        )
    ]