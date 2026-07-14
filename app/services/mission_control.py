import time
from dataclasses import dataclass


@dataclass
class ActiveMission:
    asset_id: str
    event_id: str

    start_latitude: float
    start_longitude: float

    target_latitude: float
    target_longitude: float

    cruise_speed_mps: float
    assigned_at: float


_active_missions: dict[str, ActiveMission] = {}


def assign_mission(
    asset_id: str,
    event_id: str,
    start_latitude: float,
    start_longitude: float,
    target_latitude: float,
    target_longitude: float,
    cruise_speed_mps: float,
) -> ActiveMission:
    """
    Creates a mission for a drone.

    If the drone is already assigned to the same event
    and target, the original mission is preserved.
    """

    current_mission = _active_missions.get(asset_id)

    if (
        current_mission is not None
        and current_mission.event_id == event_id
        and current_mission.target_latitude == target_latitude
        and current_mission.target_longitude == target_longitude
    ):
        return current_mission

    mission = ActiveMission(
        asset_id=asset_id,
        event_id=event_id,
        start_latitude=start_latitude,
        start_longitude=start_longitude,
        target_latitude=target_latitude,
        target_longitude=target_longitude,
        cruise_speed_mps=max(
            1.0,
            cruise_speed_mps,
        ),
        assigned_at=time.monotonic(),
    )

    _active_missions[asset_id] = mission

    return mission


def get_active_mission(
    asset_id: str,
) -> ActiveMission | None:
    return _active_missions.get(asset_id)


def keep_only_missions(
    assigned_asset_ids: set[str],
) -> None:
    """
    Removes missions belonging to drones that are
    no longer assigned to an active incident.
    """

    asset_ids_to_remove = [
        asset_id
        for asset_id in _active_missions
        if asset_id not in assigned_asset_ids
    ]

    for asset_id in asset_ids_to_remove:
        del _active_missions[asset_id]


def clear_all_missions() -> None:
    _active_missions.clear()