const completedRouteLayers = new Map();
const pendingRouteLayers = new Map();
const transitRouteLayers = new Map();
const missionWaypointLayers = new Map();


function waypointPosition(waypoint) {
    return [
        waypoint.latitude,
        waypoint.longitude,
    ];
}


function assetPosition(asset) {
    if (!asset || !asset.telemetry) {
        return null;
    }

    return [
        asset.telemetry.latitude,
        asset.telemetry.longitude,
    ];
}


function getAssignedDrone(plan, assets) {
    /*
     * Busca exclusivamente el activo asignado
     * por el backend a este plan.
     */
    return assets.find(
        (asset) => (
            asset.id === plan.assigned_asset_id
        )
    );
}


function pendingColor(plan) {
    if (plan.scenario === "maritime_sar") {
        return "#f59e0b";
    }

    /*
     * Colores diferentes para distinguir
     * las misiones Wildfire.
     */
    if (plan.assigned_asset_id === "sim-001") {
        return "#fb7185";
    }

    if (plan.assigned_asset_id === "sim-002") {
        return "#a78bfa";
    }

    return "#fbbf24";
}


function formatPattern(pattern) {
    if (pattern === "parallel_track") {
        return "Parallel track";
    }

    return pattern.replaceAll("_", " ");
}


function formatStatus(status) {
    return status.replaceAll("_", " ");
}


function removeLayer(
    layerMap,
    planId
) {
    const layer = layerMap.get(planId);

    if (!layer) {
        return;
    }

    map.removeLayer(layer);
    layerMap.delete(planId);
}


function updatePolyline(
    layerMap,
    planId,
    positions,
    options,
    popupContent
) {
    if (positions.length < 2) {
        removeLayer(
            layerMap,
            planId
        );

        return;
    }

    let layer = layerMap.get(planId);

    if (!layer) {
        layer = L.polyline(
            positions,
            options
        ).addTo(map);

        layer.bindPopup(
            popupContent
        );

        layerMap.set(
            planId,
            layer
        );

        return;
    }

    layer.setLatLngs(
        positions
    );

    layer.setStyle(
        options
    );

    layer.setPopupContent(
        popupContent
    );
}


function completedPositions(
    plan,
    dronePosition
) {
    const coverage = Number(
        plan.coverage_percent
    );

    if (
        plan.status === "planned"
        || coverage <= 0
    ) {
        return [];
    }

    if (plan.status === "completed") {
        return plan.waypoints.map(
            waypointPosition
        );
    }

    const currentIndex = Math.min(
        plan.current_waypoint_index,
        plan.waypoints.length - 1
    );

    const positions = plan.waypoints
        .slice(0, currentIndex)
        .map(waypointPosition);

    if (dronePosition) {
        positions.push(
            dronePosition
        );
    }

    return positions;
}


function pendingPositions(
    plan,
    dronePosition
) {
    const coverage = Number(
        plan.coverage_percent
    );

    if (plan.status === "completed") {
        return [];
    }

    if (
        plan.status === "planned"
        || coverage <= 0
    ) {
        return plan.waypoints.map(
            waypointPosition
        );
    }

    const currentIndex = Math.min(
        plan.current_waypoint_index,
        plan.waypoints.length - 1
    );

    const positions = [];

    if (dronePosition) {
        positions.push(
            dronePosition
        );
    }

    positions.push(
        ...plan.waypoints
            .slice(currentIndex)
            .map(waypointPosition)
    );

    return positions;
}


function updateTransitRoute(
    plan,
    dronePosition
) {
    const isInTransit = (
        plan.status === "planned"
        && Number(plan.coverage_percent) <= 0
        && dronePosition !== null
        && plan.waypoints.length > 0
    );

    if (!isInTransit) {
        removeLayer(
            transitRouteLayers,
            plan.id
        );

        return;
    }

    const entryPosition = waypointPosition(
        plan.waypoints[0]
    );

    updatePolyline(
        transitRouteLayers,
        plan.id,
        [
            dronePosition,
            entryPosition,
        ],
        {
            color: "#38bdf8",
            weight: 3,
            opacity: 0.9,
            dashArray: "5 8",
        },
        `
            <strong>Transit to search area</strong><br>
            Assigned asset:
            ${plan.assigned_asset_name}<br>
            Coverage remains at 0% until the drone
            reaches the first waypoint.
        `
    );
}


function updateWaypoints(
    plan,
    routeColor
) {
    removeLayer(
        missionWaypointLayers,
        plan.id
    );

    if (plan.waypoints.length === 0) {
        return;
    }

    const currentIndex = Math.min(
        plan.current_waypoint_index,
        plan.waypoints.length - 1
    );

    const markers = plan.waypoints.map(
        (waypoint, index) => {
            const completed = (
                plan.status === "completed"
                || (
                    plan.status === "in_progress"
                    && index < currentIndex
                )
            );

            const current = (
                plan.status !== "completed"
                && index === currentIndex
            );

            let color = routeColor;
            let radius = 4;
            let fillOpacity = 0.8;

            if (completed) {
                color = "#22c55e";
                fillOpacity = 0.95;
            }

            if (current) {
                color = "#ffffff";
                radius = 7;
                fillOpacity = 1;
            }

            const marker = L.circleMarker(
                waypointPosition(waypoint),
                {
                    radius: radius,
                    color: color,
                    fillColor: color,
                    fillOpacity: fillOpacity,
                    weight: 2,
                }
            );

            marker.bindTooltip(
                `
                    ${plan.assigned_asset_name}<br>
                    Waypoint ${waypoint.sequence + 1}<br>
                    Action: ${waypoint.action}<br>
                    Altitude: ${waypoint.altitude_m} m
                `,
                {
                    direction: "top",
                }
            );

            return marker;
        }
    );

    const group = L.layerGroup(
        markers
    ).addTo(map);

    missionWaypointLayers.set(
        plan.id,
        group
    );
}


function updateMissionRoute(
    plan,
    assets
) {
    const assignedDrone = getAssignedDrone(
        plan,
        assets
    );

    const dronePosition = assetPosition(
        assignedDrone
    );

    const routeColor = pendingColor(
        plan
    );

    const coverage = Number(
        plan.coverage_percent
    ).toFixed(1);

    const popupContent = `
        <strong>Automatic search route</strong><br>
        Assigned asset:
        ${plan.assigned_asset_name}<br>
        Event:
        ${plan.related_event_id}<br>
        Pattern:
        ${formatPattern(plan.pattern)}<br>
        Waypoints:
        ${plan.waypoint_count}<br>
        Track spacing:
        ${plan.track_spacing_m} m<br>
        Search altitude:
        ${plan.altitude_m} m<br>
        Status:
        ${formatStatus(plan.status)}<br>
        Coverage:
        ${coverage}%
    `;

    updatePolyline(
        completedRouteLayers,
        plan.id,
        completedPositions(
            plan,
            dronePosition
        ),
        {
            color: "#22c55e",
            weight: 5,
            opacity: 0.95,
        },
        popupContent
    );

    updatePolyline(
        pendingRouteLayers,
        plan.id,
        pendingPositions(
            plan,
            dronePosition
        ),
        {
            color: routeColor,
            weight: 3,
            opacity: 0.9,
            dashArray: "10 7",
        },
        popupContent
    );

    updateTransitRoute(
        plan,
        dronePosition
    );

    updateWaypoints(
        plan,
        routeColor
    );
}


function removeStalePlans(
    activePlanIds
) {
    const layerMaps = [
        completedRouteLayers,
        pendingRouteLayers,
        transitRouteLayers,
        missionWaypointLayers,
    ];

    layerMaps.forEach(
        (layerMap) => {
            const planIds = [
                ...layerMap.keys(),
            ];

            planIds.forEach(
                (planId) => {
                    if (!activePlanIds.has(planId)) {
                        removeLayer(
                            layerMap,
                            planId
                        );
                    }
                }
            );
        }
    );
}


function operationalMessage(plan) {
    if (plan.status === "planned") {
        return (
            `${plan.assigned_asset_name} is in transit. `
            + "Search coverage has not started."
        );
    }

    if (plan.status === "completed") {
        return (
            `${plan.assigned_asset_name} completed `
            + "the full planned search route."
        );
    }

    return (
        `${plan.assigned_asset_name} is searching. `
        + "Green is completed and the dashed route "
        + "remains pending."
    );
}


function renderMissionPlans(plans) {
    const container = document.getElementById(
        "mission-plan-list"
    );

    if (!container) {
        return;
    }

    if (plans.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                No automatic search mission has been generated.
            </div>
        `;

        return;
    }

    container.innerHTML = plans.map(
        (plan) => {
            const coverage = Number(
                plan.coverage_percent
            ).toFixed(1);

            const currentWaypoint = (
                plan.status === "completed"
                    ? plan.waypoint_count
                    : Math.min(
                        plan.current_waypoint_index + 1,
                        plan.waypoint_count
                    )
            );

            return `
                <div class="mission-plan-card">
                    <div class="mission-plan-title">
                        ${plan.assigned_asset_name}
                        ·
                        ${plan.related_event_id}
                    </div>

                    <div class="mission-plan-detail">
                        <strong>Assigned asset:</strong>
                        ${plan.assigned_asset_name}
                        (${plan.assigned_asset_id})
                    </div>

                    <div class="mission-plan-detail">
                        <strong>Pattern:</strong>
                        ${formatPattern(plan.pattern)}
                    </div>

                    <div class="mission-plan-detail">
                        <strong>Waypoints:</strong>
                        ${plan.waypoint_count}

                        ·

                        <strong>Current:</strong>
                        ${currentWaypoint}
                    </div>

                    <div class="mission-plan-detail">
                        <strong>Track spacing:</strong>
                        ${plan.track_spacing_m} m

                        ·

                        <strong>Altitude:</strong>
                        ${plan.altitude_m} m
                    </div>

                    <div class="mission-plan-detail">
                        <strong>Route length:</strong>
                        ${Math.round(
                            plan.estimated_path_length_m
                        )} m

                        ·

                        <strong>Duration:</strong>
                        ${plan.estimated_duration_minutes} min
                    </div>

                    <div class="mission-plan-detail">
                        <strong>Status:</strong>
                        ${formatStatus(plan.status)}

                        ·

                        <strong>Coverage:</strong>
                        ${coverage}%
                    </div>

                    <div class="mission-progress-track">
                        <div
                            class="mission-progress-fill"
                            style="width: ${coverage}%"
                        ></div>
                    </div>

                    <div class="mission-plan-summary">
                        ${operationalMessage(plan)}

                        <br><br>

                        ${plan.calculation_summary}
                    </div>
                </div>
            `;
        }
    ).join("");
}


async function refreshMissionPlanner() {
    try {
        const [
            plansResponse,
            assetsResponse,
        ] = await Promise.all([
            fetch(
                "/mission-plans",
                {
                    cache: "no-store",
                }
            ),
            fetch(
                "/assets",
                {
                    cache: "no-store",
                }
            ),
        ]);

        if (
            !plansResponse.ok
            || !assetsResponse.ok
        ) {
            throw new Error(
                "Unable to load mission execution data"
            );
        }

        const plans = await plansResponse.json();
        const assets = await assetsResponse.json();

        const activePlanIds = new Set(
            plans.map(
                (plan) => plan.id
            )
        );

        removeStalePlans(
            activePlanIds
        );

        plans.forEach(
            (plan) => {
                updateMissionRoute(
                    plan,
                    assets
                );
            }
        );

        renderMissionPlans(
            plans
        );
    } catch (error) {
        console.error(
            "Unable to update Mission Planner:",
            error
        );
    }
}


refreshMissionPlanner();

setInterval(
    refreshMissionPlanner,
    2000
);