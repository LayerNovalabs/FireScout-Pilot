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


async function refreshAssets() {
    try {
        const response = await fetch("/assets", {
            cache: "no-store",
        });

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        const assets = await response.json();
        const cards = document.querySelectorAll(".asset");

        assets.forEach((asset, index) => {
            const card = cards[index];

            if (!card) {
                return;
            }

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

            batteryElement.textContent = `${asset.battery}%`;
            batteryElement.className = getBatteryClass(
                asset.battery
            );

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
        });
    } catch (error) {
        console.error("Unable to update assets:", error);
    }
}


refreshAssets();
setInterval(refreshAssets, 2000);