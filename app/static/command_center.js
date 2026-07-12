const map = L.map("map").setView(
    [41.3874, 2.1686],
    14
);

L.tileLayer(
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        maxZoom: 19,
        attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">' +
            "OpenStreetMap</a> contributors",
    }
).addTo(map);


const assetMarkers = new Map();
let mapHasCentered = false;


function capitalize(value) {
    return value.charAt(0).toUpperCase() + value.slice(1);
}


function getBatteryClass(battery) {
    if (battery <= 15) {
        return "battery-critical";
    }

    if (battery <= 30) {
        return "battery-warning";
    }

    return "";
}


function getMarkerColor(asset) {
    if (asset.status === "warning") {
        return "#f59e0b";
    }

    return "#38bdf8";
}


function updateAssetMarker(asset) {
    if (!asset.telemetry) {
        return;
    }

    const position = [
        asset.telemetry.latitude,
        asset.telemetry.longitude,
    ];

    const markerColor = getMarkerColor(asset);
    let marker = assetMarkers.get(asset.id);

    const popupContent = `
        <strong>${asset.name}</strong><br>
        Status: ${capitalize(asset.status)}<br>
        Battery: ${asset.battery}%<br>
        Altitude: ${asset.telemetry.altitude} m<br>
        Speed: ${asset.telemetry.speed} m/s<br>
        Heading: ${asset.telemetry.heading}°
    `;

    if (!marker) {
        marker = L.circleMarker(
            position,
            {
                radius: 9,
                color: markerColor,
                fillColor: markerColor,
                fillOpacity: 0.9,
                weight: 3,
            }
        ).addTo(map);

        marker.bindTooltip(
            asset.name,
            {
                direction: "top",
                offset: [0, -8],
            }
        );

        marker.bindPopup(popupContent);
        assetMarkers.set(asset.id, marker);
    } else {
        marker.setLatLng(position);

        marker.setStyle({
            color: markerColor,
            fillColor: markerColor,
        });

        marker.setPopupContent(popupContent);
    }
}


function centerMapOnce() {
    if (mapHasCentered || assetMarkers.size === 0) {
        return;
    }

    const markers = Array.from(assetMarkers.values());
    const markerGroup = L.featureGroup(markers);

    map.fitBounds(
        markerGroup.getBounds(),
        {
            padding: [40, 40],
            maxZoom: 15,
        }
    );

    mapHasCentered = true;
}


async function refreshAssets() {
    try {
        const response = await fetch(
            "/assets",
            {
                cache: "no-store",
            }
        );

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        const assets = await response.json();
        const cards = document.querySelectorAll(".asset");

        assets.forEach((asset, index) => {
            const card = cards[index];

            if (card) {
                const nameElement = card.querySelector(
                    ".asset-name span:first-child"
                );

                const batteryElement = card.querySelector(
                    ".asset-name span:last-child"
                );

                const detailsElement = card.querySelector(
                    ".asset-details"
                );

                const positionElement = card.querySelector(
                    ".asset-position"
                );

                nameElement.textContent = asset.name;

                batteryElement.textContent =
                    `${asset.battery}%`;

                batteryElement.className =
                    getBatteryClass(asset.battery);

                const statusClass =
                    asset.status === "warning"
                        ? "status-warning"
                        : "status-active";

                if (asset.telemetry) {
                    detailsElement.innerHTML = `
                        <span class="${statusClass}">
                            ${capitalize(asset.status)}
                        </span>
                        · ${asset.telemetry.altitude} m
                        · ${asset.telemetry.speed} m/s
                        · ${asset.telemetry.heading}°
                    `;

                    positionElement.textContent =
                        `${asset.telemetry.latitude}, ` +
                        `${asset.telemetry.longitude}`;
                } else {
                    detailsElement.innerHTML = `
                        <span class="${statusClass}">
                            ${capitalize(asset.status)}
                        </span>
                        · No telemetry
                    `;

                    positionElement.textContent = "";
                }
            }

            updateAssetMarker(asset);
        });

        centerMapOnce();
    } catch (error) {
        console.error(
            "Unable to update assets:",
            error
        );
    }
}


refreshAssets();
setInterval(refreshAssets, 2000);
const eventMarkers = new Map();


function getEventColor(event) {
    if (event.severity === "critical") {
        return "#ef4444";
    }

    if (event.severity === "warning") {
        return "#f59e0b";
    }

    return "#38bdf8";
}


function updateEventMarker(event) {
    if (!event.active) {
        return;
    }

    const position = [
        event.latitude,
        event.longitude,
    ];

    const color = getEventColor(event);
    let marker = eventMarkers.get(event.id);

    const confidence = Math.round(event.confidence * 100);

    const popupContent = `
        <strong>🔥 ${event.title}</strong><br>
        ${event.description}<br>
        Severity: ${capitalize(event.severity)}<br>
        Confidence: ${confidence}%
    `;

    if (!marker) {
        marker = L.circle(
            position,
            {
                radius: 120,
                color: color,
                fillColor: color,
                fillOpacity: 0.3,
                weight: 3,
            }
        ).addTo(map);

        marker.bindTooltip(
            `🔥 ${event.title}`,
            {
                permanent: true,
                direction: "top",
            }
        );

        marker.bindPopup(popupContent);
        eventMarkers.set(event.id, marker);
    } else {
        marker.setLatLng(position);

        marker.setStyle({
            color: color,
            fillColor: color,
        });

        marker.setTooltipContent(
            `🔥 ${event.title}`
        );

        marker.setPopupContent(popupContent);
    }
}


async function refreshEvents() {
    try {
        const response = await fetch(
            "/events",
            {
                cache: "no-store",
            }
        );

        if (!response.ok) {
            throw new Error(
                `HTTP error: ${response.status}`
            );
        }

        const events = await response.json();

        events.forEach((event) => {
            updateEventMarker(event);
        });
    } catch (error) {
        console.error(
            "Unable to update events:",
            error
        );
    }
}


refreshEvents();
setInterval(refreshEvents, 5000);
