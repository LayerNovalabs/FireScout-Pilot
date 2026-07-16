const searchAreaLayers = new Map();
const searchAreaCenterMarkers = new Map();

let searchAreaMapHasCentered = false;


function capitalizeSearchValue(value) {
    if (!value) {
        return "";
    }

    return value.charAt(0).toUpperCase() + value.slice(1);
}


function getSearchAreaColor(searchArea) {
    if (searchArea.scenario === "maritime_sar") {
        return "#2dd4bf";
    }

    return "#38bdf8";
}


function updateSearchAreaLayer(searchArea) {
    const positions = searchArea.polygon.map(
        (point) => [
            point.latitude,
            point.longitude,
        ]
    );

    const color = getSearchAreaColor(searchArea);
    const confidence = Math.round(
        searchArea.confidence * 100
    );

    let layer = searchAreaLayers.get(
        searchArea.id
    );

    let centerMarker = searchAreaCenterMarkers.get(
        searchArea.id
    );

    const scenarioName = capitalizeSearchValue(
        searchArea.scenario.replaceAll("_", " ")
    );

    const popupContent = `
        <strong>Calculated search area</strong><br>
        Scenario: ${scenarioName}<br>
        Confidence: ${confidence}%<br>
        Elapsed time: ${searchArea.elapsed_minutes} min<br>
        Major axis:
        ${Math.round(searchArea.semi_major_axis_m * 2)} m<br>
        Minor axis:
        ${Math.round(searchArea.semi_minor_axis_m * 2)} m<br>
        Orientation:
        ${searchArea.orientation_degrees}°<br>
        Projected displacement:
        ${searchArea.displacement_m} m
    `;

    if (!layer) {
        layer = L.polygon(
            positions,
            {
                color: color,
                fillColor: color,
                fillOpacity: 0.16,
                weight: 3,
                dashArray: "8 6",
            }
        ).addTo(map);

        layer.bindPopup(popupContent);

        searchAreaLayers.set(
            searchArea.id,
            layer
        );
    } else {
        layer.setLatLngs(positions);

        layer.setStyle({
            color: color,
            fillColor: color,
        });

        layer.setPopupContent(
            popupContent
        );
    }

    const centerPosition = [
        searchArea.estimated_center.latitude,
        searchArea.estimated_center.longitude,
    ];

    if (!centerMarker) {
        centerMarker = L.circleMarker(
            centerPosition,
            {
                radius: 6,
                color: color,
                fillColor: color,
                fillOpacity: 1,
                weight: 2,
            }
        ).addTo(map);

        centerMarker.bindTooltip(
            "Estimated search center",
            {
                direction: "top",
            }
        );

        searchAreaCenterMarkers.set(
            searchArea.id,
            centerMarker
        );
    } else {
        centerMarker.setLatLng(
            centerPosition
        );

        centerMarker.setStyle({
            color: color,
            fillColor: color,
        });
    }
}


function removeStaleSearchAreas(activeAreaIds) {
    searchAreaLayers.forEach(
        (layer, areaId) => {
            if (!activeAreaIds.has(areaId)) {
                map.removeLayer(layer);

                searchAreaLayers.delete(
                    areaId
                );
            }
        }
    );

    searchAreaCenterMarkers.forEach(
        (marker, areaId) => {
            if (!activeAreaIds.has(areaId)) {
                map.removeLayer(marker);

                searchAreaCenterMarkers.delete(
                    areaId
                );
            }
        }
    );
}


function renderEnvironment(environment) {
    const container = document.getElementById(
        "environment-summary"
    );

    if (!container) {
        return;
    }

    let scenarioSpecificDetails;

    if (environment.scenario === "maritime_sar") {
        scenarioSpecificDetails = `
            <div class="intelligence-detail">
                <strong>Surface current:</strong>
                ${environment.current_speed_mps} m/s toward
                ${environment.current_direction_degrees}°
            </div>

            <div class="intelligence-detail">
                <strong>Significant waves:</strong>
                ${environment.significant_wave_height_m} m toward
                ${environment.wave_direction_degrees}°
            </div>
        `;
    } else {
        scenarioSpecificDetails = `
            <div class="intelligence-detail">
                <strong>Temperature:</strong>
                ${environment.temperature_celsius} °C
            </div>

            <div class="intelligence-detail">
                <strong>Smoke density:</strong>
                ${Math.round(
                    environment.smoke_density * 100
                )}%
            </div>

            <div class="intelligence-detail">
                <strong>Terrain slope:</strong>
                ${environment.slope_percent}% toward
                ${environment.slope_direction_degrees}°
            </div>
        `;
    }

    container.innerHTML = `
        <div class="environment-card">
            <div class="intelligence-title">
                Environmental Engine
            </div>

            <div class="intelligence-detail">
                <strong>Wind:</strong>
                ${environment.wind_speed_mps} m/s toward
                ${environment.wind_direction_degrees}°
            </div>

            <div class="intelligence-detail">
                <strong>Visibility:</strong>
                ${environment.visibility_km} km
            </div>

            ${scenarioSpecificDetails}

            <div class="intelligence-summary">
                Source: ${environment.source}.
                Bearings indicate the direction in
                which each vector moves.
            </div>
        </div>
    `;
}


function renderSearchAreas(searchAreas) {
    const container = document.getElementById(
        "search-area-list"
    );

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (searchAreas.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                No active search area could be calculated.
            </div>
        `;

        return;
    }

    searchAreas.forEach(
        (searchArea) => {
            const confidence = Math.round(
                searchArea.confidence * 100
            );

            const card = document.createElement(
                "div"
            );

            card.className = "search-area-card";

            card.innerHTML = `
                <div class="intelligence-title">
                    Search area ·
                    ${searchArea.related_event_id}
                </div>

                <div class="intelligence-detail">
                    <strong>Estimated center:</strong>
                    ${searchArea.estimated_center.latitude},
                    ${searchArea.estimated_center.longitude}
                </div>

                <div class="intelligence-detail">
                    <strong>Coverage ellipse:</strong>
                    ${Math.round(
                        searchArea.semi_major_axis_m * 2
                    )}
                    ×
                    ${Math.round(
                        searchArea.semi_minor_axis_m * 2
                    )}
                    m
                </div>

                <div class="intelligence-detail">
                    <strong>Confidence:</strong>
                    ${confidence}%

                    ·

                    <strong>Elapsed:</strong>
                    ${searchArea.elapsed_minutes} min
                </div>

                <div class="intelligence-detail">
                    <strong>
                        Projected displacement:
                    </strong>

                    ${searchArea.displacement_m} m toward
                    ${searchArea.orientation_degrees}°
                </div>

                <div class="intelligence-summary">
                    ${searchArea.calculation_summary}
                </div>
            `;

            container.appendChild(card);
        }
    );
}


function centerSearchAreaMapOnce() {
    if (
        searchAreaMapHasCentered
        || searchAreaLayers.size === 0
    ) {
        return;
    }

    const layers = [
        ...searchAreaLayers.values(),
        ...searchAreaCenterMarkers.values(),
    ];

    const bounds = L.featureGroup(
        layers
    ).getBounds();

    if (bounds.isValid()) {
        map.fitBounds(
            bounds.pad(0.25)
        );

        searchAreaMapHasCentered = true;
    }
}


async function refreshSearchIntelligence() {
    try {
        const [
            environmentResponse,
            searchAreasResponse,
        ] = await Promise.all([
            fetch(
                "/environment",
                {
                    cache: "no-store",
                }
            ),
            fetch(
                "/search-areas",
                {
                    cache: "no-store",
                }
            ),
        ]);

        if (
            !environmentResponse.ok
            || !searchAreasResponse.ok
        ) {
            throw new Error(
                "Unable to load search intelligence"
            );
        }

        const environment =
            await environmentResponse.json();

        const searchAreas =
            await searchAreasResponse.json();

        const activeAreaIds = new Set(
            searchAreas.map(
                (searchArea) => searchArea.id
            )
        );

        removeStaleSearchAreas(
            activeAreaIds
        );

        searchAreas.forEach(
            updateSearchAreaLayer
        );

        renderEnvironment(
            environment
        );

        renderSearchAreas(
            searchAreas
        );

        centerSearchAreaMapOnce();
    } catch (error) {
        console.error(
            "Unable to update search intelligence:",
            error
        );
    }
}


refreshSearchIntelligence();

setInterval(
    refreshSearchIntelligence,
    10000
);