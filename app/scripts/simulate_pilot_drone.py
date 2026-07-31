import json
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = (
    "http://127.0.0.1:8000"
    "/api/drones/telemetry"
)

DRONE_ID = "firescout-pilot-001"

UPDATE_INTERVAL_SECONDS = 2.0


ROUTE = [
    (41.3851, 2.1734),
    (41.3855, 2.1740),
    (41.3860, 2.1747),
    (41.3865, 2.1752),
    (41.3870, 2.1747),
    (41.3874, 2.1740),
    (41.3870, 2.1733),
    (41.3865, 2.1728),
    (41.3860, 2.1729),
    (41.3855, 2.1731),
]


def send_telemetry(
    latitude: float,
    longitude: float,
    battery_percent: int,
    heading_degrees: float,
) -> None:
    """
    Envía una lectura de telemetría
    al backend local de FireScout.
    """

    payload = {
        "drone_id": DRONE_ID,
        "latitude": latitude,
        "longitude": longitude,
        "altitude_m": 45.0,
        "speed_mps": 5.0,
        "heading_degrees": heading_degrees,
        "battery_percent": battery_percent,
        "flight_status": "flying",
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    encoded_payload = json.dumps(
        payload
    ).encode("utf-8")

    request = Request(
        API_URL,
        data=encoded_payload,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=5,
        ) as response:
            response_body = response.read().decode(
                "utf-8"
            )

        print(
            f"Telemetry sent | "
            f"Position: {latitude:.6f}, "
            f"{longitude:.6f} | "
            f"Battery: {battery_percent}% | "
            f"HTTP: {response.status}"
        )

        if response_body:
            json.loads(response_body)

    except HTTPError as error:
        error_body = error.read().decode(
            "utf-8"
        )

        print(
            f"FireScout rejected telemetry | "
            f"HTTP {error.code} | "
            f"{error_body}"
        )

    except URLError as error:
        print(
            "Unable to connect to FireScout. "
            "Confirm that Uvicorn is running."
        )

        print(
            f"Connection error: {error.reason}"
        )


def main() -> None:
    """
    Recorre continuamente una ruta de prueba.
    """

    battery_percent = 100
    route_index = 0

    print(
        "FireScout pilot drone simulator started."
    )

    print(
        "Press Ctrl+C to stop."
    )

    try:
        while True:
            latitude, longitude = ROUTE[
                route_index
            ]

            heading_degrees = (
                route_index
                * (360.0 / len(ROUTE))
            ) % 360.0

            send_telemetry(
                latitude=latitude,
                longitude=longitude,
                battery_percent=battery_percent,
                heading_degrees=heading_degrees,
            )

            route_index = (
                route_index + 1
            ) % len(ROUTE)

            battery_percent = max(
                20,
                battery_percent - 1,
            )

            time.sleep(
                UPDATE_INTERVAL_SECONDS
            )

    except KeyboardInterrupt:
        print()
        print(
            "Pilot drone simulator stopped."
        )


if __name__ == "__main__":
    main()