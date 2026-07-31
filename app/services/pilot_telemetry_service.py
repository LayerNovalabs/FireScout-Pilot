from threading import Lock

from app.models.pilot_telemetry import (
    PilotTelemetry,
)


_TELEMETRY_BY_DRONE: dict[
    str,
    PilotTelemetry,
] = {}

_TELEMETRY_LOCK = Lock()


def save_pilot_telemetry(
    telemetry: PilotTelemetry,
) -> PilotTelemetry:
    """
    Guarda o actualiza la última telemetría
    recibida de un dron.
    """

    with _TELEMETRY_LOCK:
        _TELEMETRY_BY_DRONE[
            telemetry.drone_id
        ] = telemetry

    return telemetry


def get_all_pilot_telemetry(
) -> list[PilotTelemetry]:
    """
    Devuelve la última telemetría conocida
    de todos los drones piloto.
    """

    with _TELEMETRY_LOCK:
        return list(
            _TELEMETRY_BY_DRONE.values()
        )


def get_pilot_telemetry(
    drone_id: str,
) -> PilotTelemetry | None:
    """
    Devuelve la última telemetría conocida
    de un dron concreto.
    """

    with _TELEMETRY_LOCK:
        return _TELEMETRY_BY_DRONE.get(
            drone_id
        )


def clear_pilot_telemetry() -> None:
    """
    Elimina toda la telemetría piloto guardada.
    """

    with _TELEMETRY_LOCK:
        _TELEMETRY_BY_DRONE.clear()