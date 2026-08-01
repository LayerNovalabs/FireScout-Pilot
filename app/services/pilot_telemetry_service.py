from threading import Lock

from app.models.pilot_telemetry import (
    PilotTelemetry,
)


MAX_HISTORY_POINTS = 500


_TELEMETRY_BY_DRONE: dict[
    str,
    PilotTelemetry,
] = {}

_TELEMETRY_HISTORY_BY_DRONE: dict[
    str,
    list[PilotTelemetry],
] = {}

_TELEMETRY_LOCK = Lock()


def save_pilot_telemetry(
    telemetry: PilotTelemetry,
) -> PilotTelemetry:
    """
    Guarda la última telemetría y añade
    la lectura al historial del dron.
    """

    with _TELEMETRY_LOCK:
        _TELEMETRY_BY_DRONE[
            telemetry.drone_id
        ] = telemetry

        history = (
            _TELEMETRY_HISTORY_BY_DRONE
            .setdefault(
                telemetry.drone_id,
                [],
            )
        )

        history.append(
            telemetry
        )

        if len(history) > MAX_HISTORY_POINTS:
            del history[
                :-MAX_HISTORY_POINTS
            ]

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


def get_pilot_telemetry_history(
    drone_id: str,
) -> list[PilotTelemetry]:
    """
    Devuelve el historial de posiciones
    almacenado para un dron.
    """

    with _TELEMETRY_LOCK:
        return list(
            _TELEMETRY_HISTORY_BY_DRONE.get(
                drone_id,
                [],
            )
        )


def clear_pilot_telemetry() -> None:
    """
    Elimina la última telemetría y todos
    los historiales almacenados.
    """

    with _TELEMETRY_LOCK:
        _TELEMETRY_BY_DRONE.clear()
        _TELEMETRY_HISTORY_BY_DRONE.clear()