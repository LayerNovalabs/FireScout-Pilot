from dataclasses import dataclass
from math import atan2, cos, radians, sin, sqrt

from app.models.asset import Asset, AssetStatus, AssetType
from app.models.event import OperationalEvent


@dataclass
class AssignmentResult:
    asset: Asset
    distance_km: float
    estimated_response_minutes: int


class AssignmentEngine:
    """Selects the most suitable aerial asset for an event."""

    MIN_BATTERY = 30

    def assign(
        self,
        event: OperationalEvent,
        assets: list[Asset],
    ) -> AssignmentResult | None:
        candidates: list[AssignmentResult] = []

        for asset in assets:
            if asset.asset_type != AssetType.AERIAL_DRONE:
                continue

            if asset.status not in {
                AssetStatus.READY,
                AssetStatus.ACTIVE,
            }:
                continue

            if asset.battery is None:
                continue

            if asset.battery < self.MIN_BATTERY:
                continue

            if asset.telemetry is None:
                continue

            distance_km = self._calculate_distance(
                asset.telemetry.latitude,
                asset.telemetry.longitude,
                event.latitude,
                event.longitude,
            )

            estimated_minutes = self._estimate_response_time(
                distance_km=distance_km,
                speed_mps=asset.telemetry.speed,
            )

            candidates.append(
                AssignmentResult(
                    asset=asset,
                    distance_km=distance_km,
                    estimated_response_minutes=estimated_minutes,
                )
            )

        if not candidates:
            return None

        return min(
            candidates,
            key=lambda candidate: (
                candidate.distance_km,
                -candidate.asset.battery,
            ),
        )

    def _calculate_distance(
        self,
        latitude_1: float,
        longitude_1: float,
        latitude_2: float,
        longitude_2: float,
    ) -> float:
        earth_radius_km = 6371.0

        latitude_delta = radians(latitude_2 - latitude_1)
        longitude_delta = radians(longitude_2 - longitude_1)

        latitude_1_radians = radians(latitude_1)
        latitude_2_radians = radians(latitude_2)

        haversine_value = (
            sin(latitude_delta / 2) ** 2
            + cos(latitude_1_radians)
            * cos(latitude_2_radians)
            * sin(longitude_delta / 2) ** 2
        )

        angular_distance = 2 * atan2(
            sqrt(haversine_value),
            sqrt(1 - haversine_value),
        )

        return round(
            earth_radius_km * angular_distance,
            2,
        )

    def _estimate_response_time(
        self,
        distance_km: float,
        speed_mps: float,
    ) -> int:
        if speed_mps <= 0:
            return 999

        distance_meters = distance_km * 1000
        seconds = distance_meters / speed_mps
        minutes = seconds / 60

        return max(1, round(minutes))