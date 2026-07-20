const sensorDetectionMarkers = new Map();
const sensorDetectionCircles = new Map();
const previousDetectionStatuses = new Map();

let activeOperatorNotification = null;
let operatorNotificationTimeout = null;


function injectSensorDetectionStyles() {
    if (
        document.getElementById(
            "sensor-detection-styles"
        )
    ) {
        return;
    }

    const style = document.createElement(
        "style"
    );

    style.id = "sensor-detection-styles";

    style.textContent = `
        .sensor-detection-panel {
            position: fixed;
            top: 90px;
            right: 20px;
            width: 340px;
            max-height: calc(100vh - 120px);
            overflow-y: auto;
            z-index: 1100;
            padding: 14px;
            border: 1px solid rgba(148, 163, 184, 0.3);
            border-radius: 12px;
            background: rgba(15, 23, 42, 0.94);
            color: #e2e8f0;
            box-shadow: 0 14px 40px rgba(0, 0, 0, 0.35);
            backdrop-filter: blur(10px);
        }

        .sensor-detection-heading {
            margin-bottom: 12px;
            font-size: 15px;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .sensor-card {
            margin-bottom: 10px;
            padding: 11px;
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 9px;
            background: rgba(30, 41, 59, 0.84);
        }

        .sensor-card:last-child {
            margin-bottom: 0;
        }

        .sensor-card-title {
            margin-bottom: 6px;
            font-weight: 700;
        }

        .sensor-detail {
            margin-top: 4px;
            font-size: 12px;
            line-height: 1.45;
            color: #cbd5e1;
        }

        .sensor-status {
            display: inline-block;
            margin-top: 7px;
            padding: 3px 8px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }

        .sensor-status-waiting {
            background: rgba(100, 116, 139, 0.24);
            color: #cbd5e1;
        }

        .sensor-status-scanning {
            background: rgba(56, 189, 248, 0.18);
            color: #7dd3fc;
        }

        .sensor-status-possible {
            background: rgba(245, 158, 11, 0.22);
            color: #fbbf24;
        }

        .sensor-status-confirmed {
            background: rgba(239, 68, 68, 0.24);
            color: #fca5a5;
        }

        .sensor-alert {
            margin-bottom: 12px;
            padding: 11px;
            border: 1px solid rgba(239, 68, 68, 0.65);
            border-radius: 9px;
            background: rgba(127, 29, 29, 0.88);
            color: #fee2e2;
            font-size: 13px;
            font-weight: 700;
            line-height: 1.45;
        }

        .victim-marker {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 34px;
            height: 34px;
            border: 3px solid #ffffff;
            border-radius: 50%;
            background: #f59e0b;
            color: #ffffff;
            font-size: 18px;
            box-shadow:
                0 0 0 6px rgba(245, 158, 11, 0.28),
                0 4px 14px rgba(0, 0, 0, 0.55);
        }

        .victim-marker-confirmed {
            background: #ef4444;
            animation: victim-pulse 1.2s infinite;
            box-shadow:
                0 0 0 7px rgba(239, 68, 68, 0.32),
                0 4px 14px rgba(0, 0, 0, 0.55);
        }

        @keyframes victim-pulse {
            0% {
                transform: scale(1);
            }

            50% {
                transform: scale(1.18);
            }

            100% {
                transform: scale(1);
            }
        }

        .operator-detection-notification {
            position: fixed;
            top: 20px;
            left: 50%;
            z-index: 5000;
            width: min(460px, calc(100% - 32px));
            padding: 15px 18px;
            border: 1px solid rgba(239, 68, 68, 0.85);
            border-radius: 12px;
            background: rgba(127, 29, 29, 0.96);
            color: #fee2e2;
            box-shadow: 0 16px 45px rgba(0, 0, 0, 0.5);
            cursor: pointer;
            opacity: 0;
            transform: translate(-50%, -30px);
            transition:
                opacity 0.25s ease,
                transform 0.25s ease;
        }

        .operator-detection-notification.visible {
            opacity: 1;
            transform: translate(-50%, 0);
        }

        .operator-notification-title {
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .operator-notification-message {
            margin-top: 6px;
            font-size: 13px;
            line-height: 1.4;
        }

        .operator-notification-action {
            margin-top: 8px;
            color: #fecaca;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }

        .sensor-panel-highlight {
            animation: sensor-panel-focus 2.4s ease-out;
        }

        @keyframes sensor-panel-focus {
            0% {
                box-shadow:
                    0 0 0 4px rgba(239, 68, 68, 0.8),
                    0 14px 40px rgba(0, 0, 0, 0.4);
            }

            100% {
                box-shadow:
                    0 14px 40px rgba(0, 0, 0, 0.4);
            }
        }

        @media (max-width: 900px) {
            .sensor-detection-panel {
                top: auto;
                right: 10px;
                bottom: 10px;
                left: 10px;
                width: auto;
                max-height: 40vh;
            }
        }
    `;

    document.head.appendChild(
        style
    );
}


function createSensorDetectionPanel() {
    let panel = document.getElementById(
        "sensor-detection-panel"
    );

    if (panel) {
        return panel;
    }

    panel = document.createElement(
        "section"
    );

    panel.id = "sensor-detection-panel";
    panel.className = (
        "sensor-detection-panel"
    );

    panel.innerHTML = `
        <div class="sensor-detection-heading">
            Sensor Intelligence
        </div>

        <div id="sensor-alert-list"></div>

        <div id="sensor-status-list">
            Loading sensor information...
        </div>
    `;

    document.body.appendChild(
        panel
    );

    return panel;
}


function formatSensorType(sensorType) {
    return sensorType
        .replaceAll("_", " ")
        .replace(
            /\b\w/g,
            (letter) => letter.toUpperCase()
        );
}


function detectionColor(status) {
    if (status === "confirmed") {
        return "#ef4444";
    }

    return "#f59e0b";
}


function detectionStatusLabel(status) {
    if (status === "confirmed") {
        return "Confirmed";
    }

    if (status === "possible") {
        return "Possible";
    }

    return "No contact";
}


function markerIcon(detection) {
    const confirmed = (
        detection.status === "confirmed"
    );

    return L.divIcon({
        className: "",
        html: `
            <div class="
                victim-marker
                ${
                    confirmed
                        ? "victim-marker-confirmed"
                        : ""
                }
            ">
                ⚠
            </div>
        `,
        iconSize: [
            34,
            34,
        ],
        iconAnchor: [
            17,
            17,
        ],
        popupAnchor: [
            0,
            -18,
        ],
    });
}


function detectionPopup(detection) {
    return `
        <strong>
            ${detectionStatusLabel(
                detection.status
            )} person detection
        </strong>

        <br>

        Detected by:
        ${detection.source_asset_name}

        <br>

        Event:
        ${detection.related_event_id}

        <br>

        Sensor:
        ${formatSensorType(
            detection.sensor_type
        )}

        <br>

        Confidence:
        ${Number(
            detection.confidence_percent
        ).toFixed(1)}%

        <br>

        Coordinates:
        ${Number(
            detection.latitude
        ).toFixed(6)},
        ${Number(
            detection.longitude
        ).toFixed(6)}

        <br>

        Distance from drone:
        ${Number(
            detection.distance_to_target_m
        ).toFixed(1)} m
    `;
}


function focusSensorIntelligencePanel() {
    const sensorPanel = document.getElementById(
        "sensor-detection-panel"
    );

    const bottomSection = document.getElementById(
        "command-center-bottom-section"
    );

    const target = (
        sensorPanel
        || bottomSection
    );

    if (!target) {
        return;
    }

    target.scrollIntoView({
        behavior: "smooth",
        block: "start",
    });

    if (!sensorPanel) {
        return;
    }

    sensorPanel.classList.remove(
        "sensor-panel-highlight"
    );

    void sensorPanel.offsetWidth;

    sensorPanel.classList.add(
        "sensor-panel-highlight"
    );

    setTimeout(
        () => {
            sensorPanel.classList.remove(
                "sensor-panel-highlight"
            );
        },
        2500
    );
}


function closeOperatorNotification() {
    if (!activeOperatorNotification) {
        return;
    }

    const notification = (
        activeOperatorNotification
    );

    activeOperatorNotification = null;

    notification.classList.remove(
        "visible"
    );

    setTimeout(
        () => {
            notification.remove();
        },
        300
    );

    if (operatorNotificationTimeout) {
        clearTimeout(
            operatorNotificationTimeout
        );

        operatorNotificationTimeout = null;
    }
}


function showOperatorDetectionNotification(
    detection
) {
    closeOperatorNotification();

    const notification = document.createElement(
        "div"
    );

    notification.className = (
        "operator-detection-notification"
    );

    notification.setAttribute(
        "role",
        "button"
    );

    notification.setAttribute(
        "tabindex",
        "0"
    );

    notification.innerHTML = `
        <div class="operator-notification-title">
            Confirmed person detection
        </div>

        <div class="operator-notification-message">
            ${detection.source_asset_name}
            confirmed a person with
            ${Number(
                detection.confidence_percent
            ).toFixed(1)}% confidence.
        </div>

        <div class="operator-notification-action">
            Click to open Sensor Intelligence
        </div>
    `;

    const openDetectionDetails = () => {
        focusSensorIntelligencePanel();
        closeOperatorNotification();
    };

    notification.addEventListener(
        "click",
        openDetectionDetails
    );

    notification.addEventListener(
        "keydown",
        (event) => {
            if (
                event.key === "Enter"
                || event.key === " "
            ) {
                event.preventDefault();
                openDetectionDetails();
            }
        }
    );

    document.body.appendChild(
        notification
    );

    activeOperatorNotification = notification;

    requestAnimationFrame(
        () => {
            notification.classList.add(
                "visible"
            );
        }
    );

    operatorNotificationTimeout = setTimeout(
        closeOperatorNotification,
        15000
    );
}


function updateDetectionMarker(detection) {
    if (
        typeof map === "undefined"
        || typeof L === "undefined"
    ) {
        return;
    }

    const position = [
        detection.latitude,
        detection.longitude,
    ];

    let marker = sensorDetectionMarkers.get(
        detection.id
    );

    if (!marker) {
        marker = L.marker(
            position,
            {
                icon: markerIcon(detection),
                zIndexOffset: 2000,
            }
        ).addTo(map);

        marker.bindPopup(
            detectionPopup(detection)
        );

        sensorDetectionMarkers.set(
            detection.id,
            marker
        );
    } else {
        marker.setLatLng(position);
        marker.setIcon(
            markerIcon(detection)
        );
        marker.setPopupContent(
            detectionPopup(detection)
        );
    }

    let radiusCircle = (
        sensorDetectionCircles.get(
            detection.id
        )
    );

    const circleOptions = {
        radius: detection.detection_radius_m,
        color: detectionColor(
            detection.status
        ),
        weight: 2,
        opacity: 0.8,
        fillColor: detectionColor(
            detection.status
        ),
        fillOpacity: 0.08,
        dashArray: "7 7",
    };

    if (!radiusCircle) {
        radiusCircle = L.circle(
            position,
            circleOptions
        ).addTo(map);

        sensorDetectionCircles.set(
            detection.id,
            radiusCircle
        );
    } else {
        radiusCircle.setLatLng(position);
        radiusCircle.setRadius(
            detection.detection_radius_m
        );
        radiusCircle.setStyle(
            circleOptions
        );
    }

    const previousStatus = (
        previousDetectionStatuses.get(
            detection.id
        )
    );

    if (
        detection.status === "confirmed"
        && previousStatus !== "confirmed"
    ) {
        marker.openPopup();

        map.panTo(
            position,
            {
                animate: true,
            }
        );

        showOperatorDetectionNotification(
            detection
        );
    }

    previousDetectionStatuses.set(
        detection.id,
        detection.status
    );
}


function removeStaleDetectionLayers(
    activeDetectionIds
) {
    for (
        const [
            detectionId,
            marker,
        ]
        of sensorDetectionMarkers
    ) {
        if (
            !activeDetectionIds.has(
                detectionId
            )
        ) {
            map.removeLayer(marker);

            sensorDetectionMarkers.delete(
                detectionId
            );

            previousDetectionStatuses.delete(
                detectionId
            );
        }
    }

    for (
        const [
            detectionId,
            circle,
        ]
        of sensorDetectionCircles
    ) {
        if (
            !activeDetectionIds.has(
                detectionId
            )
        ) {
            map.removeLayer(circle);

            sensorDetectionCircles.delete(
                detectionId
            );
        }
    }
}


function renderDetectionAlerts(
    detections
) {
    const container = document.getElementById(
        "sensor-alert-list"
    );

    if (!container) {
        return;
    }

    const confirmedDetections = detections.filter(
        (detection) => (
            detection.status === "confirmed"
        )
    );

    if (
        confirmedDetections.length === 0
    ) {
        container.innerHTML = "";
        return;
    }

    container.innerHTML = (
        confirmedDetections.map(
            (detection) => `
                <div class="sensor-alert">
                    CONFIRMED PERSON DETECTION

                    <br>

                    ${detection.source_asset_name}

                    <br>

                    Confidence:
                    ${Number(
                        detection.confidence_percent
                    ).toFixed(1)}%

                    <br>

                    ${Number(
                        detection.latitude
                    ).toFixed(6)},
                    ${Number(
                        detection.longitude
                    ).toFixed(6)}
                </div>
            `
        ).join("")
    );
}


function findDetectionForMission(
    status,
    detections
) {
    return detections.find(
        (detection) => (
            detection.related_event_id
            === status.related_event_id
        )
    );
}


function renderSensorStatuses(
    statuses,
    detections
) {
    const container = document.getElementById(
        "sensor-status-list"
    );

    if (!container) {
        return;
    }

    if (statuses.length === 0) {
        container.innerHTML = `
            <div class="sensor-card">
                No sensor missions are active.
            </div>
        `;

        return;
    }

    container.innerHTML = statuses.map(
        (status) => {
            const detection = (
                findDetectionForMission(
                    status,
                    detections
                )
            );

            let statusClass = (
                "sensor-status-waiting"
            );

            let statusText = "Waiting";

            if (status.sensor_active) {
                statusClass = (
                    "sensor-status-scanning"
                );

                statusText = "Scanning";
            }

            if (
                detection
                && detection.status === "possible"
            ) {
                statusClass = (
                    "sensor-status-possible"
                );

                statusText = (
                    "Possible detection"
                );
            }

            if (
                detection
                && detection.status === "confirmed"
            ) {
                statusClass = (
                    "sensor-status-confirmed"
                );

                statusText = (
                    "Confirmed detection"
                );
            }

            return `
                <div class="sensor-card">
                    <div class="sensor-card-title">
                        ${status.asset_name}
                        ·
                        ${status.related_event_id}
                    </div>

                    <div class="sensor-detail">
                        <strong>Sensor:</strong>
                        ${formatSensorType(
                            status.sensor_type
                        )}
                    </div>

                    <div class="sensor-detail">
                        <strong>Effective radius:</strong>
                        ${Number(
                            status.detection_radius_m
                        ).toFixed(1)} m
                    </div>

                    <div class="sensor-detail">
                        <strong>Environment factor:</strong>
                        ${Number(
                            status.environment_factor
                        ).toFixed(2)}
                    </div>

                    <div class="sensor-detail">
                        <strong>Target distance:</strong>
                        ${
                            status.nearest_target_distance_m
                            === null
                                ? "Unknown"
                                : `${Number(
                                    status
                                        .nearest_target_distance_m
                                ).toFixed(1)} m`
                        }
                    </div>

                    <span class="
                        sensor-status
                        ${statusClass}
                    ">
                        ${statusText}
                    </span>

                    <div class="sensor-detail">
                        ${status.message}
                    </div>
                </div>
            `;
        }
    ).join("");
}


async function refreshSensorDetection() {
    try {
        const [
            detectionsResponse,
            statusesResponse,
        ] = await Promise.all([
            fetch(
                "/detections",
                {
                    cache: "no-store",
                }
            ),
            fetch(
                "/sensor-statuses",
                {
                    cache: "no-store",
                }
            ),
        ]);

        if (
            !detectionsResponse.ok
            || !statusesResponse.ok
        ) {
            throw new Error(
                "Unable to load sensor data"
            );
        }

        const detections = (
            await detectionsResponse.json()
        );

        const statuses = (
            await statusesResponse.json()
        );

        const activeDetectionIds = new Set(
            detections.map(
                (detection) => detection.id
            )
        );

        removeStaleDetectionLayers(
            activeDetectionIds
        );

        detections.forEach(
            updateDetectionMarker
        );

        renderDetectionAlerts(
            detections
        );

        renderSensorStatuses(
            statuses,
            detections
        );
    } catch (error) {
        console.error(
            "Unable to update sensor detection:",
            error
        );
    }
}


injectSensorDetectionStyles();
createSensorDetectionPanel();
refreshSensorDetection();

setInterval(
    refreshSensorDetection,
    2000
);