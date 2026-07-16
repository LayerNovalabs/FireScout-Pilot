from app.models.event import (
    EventSeverity,
    EventType,
    OperationalEvent,
)


def get_maritime_events() -> list[OperationalEvent]:
    """
    Devuelve el aviso marítimo inicial.

    La posición indicada representa la última posición
    conocida de la víctima, no su ubicación actual.
    """

    return [
        OperationalEvent(
            id="sar-event-001",
            event_type=EventType.VICTIM,
            title="Person overboard reported",
            description=(
                "Last known position received from the distress "
                "report. The current victim position is unknown."
            ),
            severity=EventSeverity.CRITICAL,
            latitude=41.3475,
            longitude=2.2470,
            confidence=0.88,
            active=True,
        )
    ]