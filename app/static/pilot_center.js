const map = L.map("pilot-map").setView(
    [41.3874, 2.1686],
    13
);

L.tileLayer(
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        maxZoom: 19,
        attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">'
            + "OpenStreetMap</a> contributors",
    }
).addTo(map);


const droneMarkers = new Map();

let mapHasCentered = false;


function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function formatStatus(status) {
    return String(status)
        .replaceAll("_", " ")
        .replace(/\b\w/g, (character) => {
            return character.toUpperCase();
        });
}


function getMarkerColor(drone) {
    if (drone.flight_status === "error") {
        return "#ef4444";
    }

    if (
        drone.battery_percent <= 20
        || drone.flight_status === "returning_home"
    ) {
        return "#f59e0b";
    }

    if (drone.flight_status === "flying") {
        return "#22c55e";
    }

    return "#38bdf8";
}


function getStatusClass(drone) {
    if (drone.flight_status === "error") {
        return "error";
    }

    if (
        drone.battery_percent <= 20
        || drone.flight_status === "returning_home"
    ) {
        return "warning";
    }

    return "";
}


function formatTimestamp(timestamp) {
    const parsedTimestamp = new Date(timestamp);

    if (Number.isNaN(parsedTimestamp.getTime())) {
        return "Unknown";
    }

    return parsedTimestamp.toLocaleString();
}


function updateDroneMarker(drone) {
    const position = [
        drone.latitude,
        drone.longitude,
    ];

    const markerColor = getMarkerColor(drone);

    const safeDroneId = escapeHtml(
        drone.drone_id
    );

    const popupContent = `
        <strong>${safeDroneId}</strong><br>
        Status: ${escapeHtml(formatStatus(drone.flight_status))}<br>
        Battery: ${drone.battery_percent}%<br>
        Altitude: ${drone.altitude_m} m<br>
        Speed: ${drone.speed_mps} m/s<br>
        Heading: ${drone.heading_degrees}°<br>
        Updated: ${escapeHtml(formatTimestamp(drone.timestamp))}
    `;

    let marker = droneMarkers.get(
        drone.drone_id
    );

    if (!marker) {
        marker = L.circleMarker(
            position,
            {
                radius: 10,
                color: markerColor,
                fillColor: markerColor,
                fillOpacity: 0.9,
                weight: 3,
            }
        ).addTo(map);

        marker.bindTooltip(
            safeDroneId,
            {
                direction: "top",
                offset: [0, -8],
            }
        );

        marker.bindPopup(
            popupContent
        );

        droneMarkers.set(
            drone.drone_id,
            marker
        );
    } else {
        marker.setLatLng(
            position
        );

        marker.setStyle({
            color: markerColor,
            fillColor: markerColor,
        });

        marker.setPopupContent(
            popupContent
        );
    }
}


function removeMissingMarkers(drones) {
    const currentDroneIds = new Set(
        drones.map((drone) => drone.drone_id)
    );

    droneMarkers.forEach(
        (marker, droneId) => {
            if (!currentDroneIds.has(droneId)) {
                map.removeLayer(marker);
                droneMarkers.delete(droneId);
            }
        }
    );
}


function centerMapOnce() {
    if (
        mapHasCentered
        || droneMarkers.size === 0
    ) {
        return;
    }

    const markerGroup = L.featureGroup(
        [...droneMarkers.values()]
    );

    map.fitBounds(
        markerGroup.getBounds(),
        {
            padding: [50, 50],
            maxZoom: 16,
        }
    );

    mapHasCentered = true;
}


function renderDroneCards(drones) {
    const droneList = document.getElementById(
        "pilot-drone-list"
    );

    const droneCount = document.getElementById(
        "drone-count"
    );

    const flyingCount = document.getElementById(
        "flying-count"
    );

    droneCount.textContent = drones.length;

    flyingCount.textContent = drones.filter(
        (drone) => drone.flight_status === "flying"
    ).length;

    droneList.innerHTML = "";

    if (drones.length === 0) {
        droneList.innerHTML = `
            <div class="empty-state">
                No pilot drones are currently sending telemetry.
            </div>
        `;

        return;
    }

    drones.forEach((drone) => {
        const card = document.createElement(
            "div"
        );

        card.className = "drone-card";

        const statusClass = getStatusClass(
            drone
        );

        card.innerHTML = `
            <div class="drone-header">
                <span>${escapeHtml(drone.drone_id)}</span>

                <span class="drone-status ${statusClass}">
                    ${escapeHtml(formatStatus(drone.flight_status))}
                </span>
            </div>

            <div class="drone-details">
                <div>
                    <strong>Battery:</strong>
                    ${drone.battery_percent}%
                </div>

                <div>
                    <strong>Altitude:</strong>
                    ${drone.altitude_m} m
                </div>

                <div>
                    <strong>Speed:</strong>
                    ${drone.speed_mps} m/s
                </div>

                <div>
                    <strong>Heading:</strong>
                    ${drone.heading_degrees}°
                </div>

                <div>
                    <strong>Position:</strong>
                    ${drone.latitude},
                    ${drone.longitude}
                </div>

                <div>
                    <strong>Updated:</strong>
                    ${escapeHtml(formatTimestamp(drone.timestamp))}
                </div>
            </div>
        `;

        droneList.appendChild(
            card
        );
    });
}


function setConnectionStatus(
    status,
    message
) {
    const dot = document.getElementById(
        "connection-dot"
    );

    const text = document.getElementById(
        "connection-text"
    );

    dot.className = "status-dot";

    if (status === "online") {
        dot.classList.add("online");
    }

    if (status === "error") {
        dot.classList.add("error");
    }

    text.textContent = message;
}


async function refreshPilotDrones() {
    try {
        const response = await fetch(
            "/api/drones",
            {
                cache: "no-store",
            }
        );

        if (!response.ok) {
            throw new Error(
                `HTTP error: ${response.status}`
            );
        }

        const drones = await response.json();

        renderDroneCards(
            drones
        );

        drones.forEach((drone) => {
            updateDroneMarker(
                drone
            );
        });

        removeMissingMarkers(
            drones
        );

        centerMapOnce();

        setConnectionStatus(
            "online",
            "Telemetry API Online"
        );
    } catch (error) {
        console.error(
            "Unable to load pilot telemetry:",
            error
        );

        setConnectionStatus(
            "error",
            "Telemetry API Error"
        );
    }
}


refreshPilotDrones();

setInterval(
    refreshPilotDrones,
    2000
);