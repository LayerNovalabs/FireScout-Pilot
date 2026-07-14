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
            title="Critical forest fire",
            description=(
                "High-temperature zone detected "
                "in the northern Collserola forest area."
            ),
            severity=EventSeverity.CRITICAL,
            latitude=41.4246,
            longitude=2.1045,
            confidence=0.97,
            active=True,
        ),
        OperationalEvent(
            id="event-002",
            event_type=EventType.FIRE,
            title="Secondary forest fire",
            description=(
                "Smoke and thermal anomaly detected "
                "near the western Collserola ridge."
            ),
            severity=EventSeverity.WARNING,
            latitude=41.4435,
            longitude=2.0820,
            confidence=0.84,
            active=True,
        ),
        OperationalEvent(
            id="event-003",
            event_type=EventType.FIRE,
            title="Possible vegetation fire",
            description=(
                "Low-intensity thermal signature detected "
                "in the southern Collserola forest zone."
            ),
            severity=EventSeverity.INFORMATION,
            latitude=41.4068,
            longitude=2.0645,
            confidence=0.68,
            active=True,
        ),
    ]