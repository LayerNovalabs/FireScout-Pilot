let timelineFocusMarker = null;
let lastTimelineEntryId = null;
let timelineCollapsed = false;


function injectOperationalTimelineStyles() {
    if (
        document.getElementById(
            "operational-timeline-styles"
        )
    ) {
        return;
    }

    const style = document.createElement(
        "style"
    );

    style.id = "operational-timeline-styles";

    style.textContent = `
        .operational-timeline-panel {
            position: fixed;
            left: 20px;
            bottom: 20px;
            width: 420px;
            max-height: 48vh;
            z-index: 1080;
            display: flex;
            flex-direction: column;
            border: 1px solid rgba(148, 163, 184, 0.3);
            border-radius: 12px;
            background: rgba(15, 23, 42, 0.95);
            color: #e2e8f0;
            box-shadow: 0 14px 40px rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(10px);
            overflow: hidden;
        }

        .operational-timeline-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            padding: 12px 14px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.2);
        }

        .operational-timeline-heading {
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }

        .operational-timeline-controls {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .operational-timeline-count {
            min-width: 28px;
            padding: 2px 7px;
            border-radius: 999px;
            background: rgba(56, 189, 248, 0.18);
            color: #7dd3fc;
            text-align: center;
            font-size: 11px;
            font-weight: 700;
        }

        .operational-timeline-toggle {
            width: 28px;
            height: 28px;
            border: 1px solid rgba(148, 163, 184, 0.3);
            border-radius: 7px;
            background: rgba(30, 41, 59, 0.85);
            color: #e2e8f0;
            cursor: pointer;
            font-size: 16px;
        }

        .operational-timeline-toggle:hover {
            background: rgba(51, 65, 85, 0.95);
        }

        .operational-timeline-body {
            padding: 10px;
            overflow-y: auto;
        }

        .operational-timeline-panel.collapsed {
            max-height: none;
        }

        .operational-timeline-panel.collapsed
        .operational-timeline-body {
            display: none;
        }

        .timeline-empty {
            padding: 16px;
            color: #94a3b8;
            text-align: center;
            font-size: 13px;
        }

        .timeline-entry {
            position: relative;
            margin-bottom: 9px;
            padding: 10px 11px 10px 15px;
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 9px;
            background: rgba(30, 41, 59, 0.82);
            cursor: default;
        }

        .timeline-entry:last-child {
            margin-bottom: 0;
        }

        .timeline-entry.has-position {
            cursor: pointer;
        }

        .timeline-entry.has-position:hover {
            background: rgba(51, 65, 85, 0.9);
        }

        .timeline-entry::before {
            position: absolute;
            top: 9px;
            bottom: 9px;
            left: 5px;
            width: 3px;
            border-radius: 999px;
            background: #64748b;
            content: "";
        }

        .timeline-entry.severity-info::before {
            background: #38bdf8;
        }

        .timeline-entry.severity-success::before {
            background: #22c55e;
        }

        .timeline-entry.severity-warning::before {
            background: #f59e0b;
        }

        .timeline-entry.severity-critical::before {
            background: #ef4444;
        }

        .timeline-entry-new {
            animation: timeline-new-entry 1.4s ease-out;
        }

        @keyframes timeline-new-entry {
            0% {
                background: rgba(56, 189, 248, 0.35);
            }

            100% {
                background: rgba(30, 41, 59, 0.82);
            }
        }

        .timeline-entry-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 10px;
        }

        .timeline-entry-title {
            font-size: 13px;
            font-weight: 750;
            color: #f8fafc;
        }

        .timeline-entry-time {
            flex: 0 0 auto;
            color: #94a3b8;
            font-size: 11px;
            font-family: monospace;
        }

        .timeline-entry-message {
            margin-top: 5px;
            color: #cbd5e1;
            font-size: 12px;
            line-height: 1.4;
        }

        .timeline-entry-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-top: 7px;
        }

        .timeline-tag {
            padding: 2px 6px;
            border-radius: 999px;
            background: rgba(100, 116, 139, 0.2);
            color: #cbd5e1;
            font-size: 10px;
            text-transform: uppercase;
        }

        .timeline-position-hint {
            margin-top: 6px;
            color: #7dd3fc;
            font-size: 10px;
        }

        @media (max-width: 900px) {
            .operational-timeline-panel {
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


function createOperationalTimelinePanel() {
    let panel = document.getElementById(
        "operational-timeline-panel"
    );

    if (panel) {
        return panel;
    }

    panel = document.createElement(
        "section"
    );

    panel.id = "operational-timeline-panel";
    panel.className = (
        "operational-timeline-panel"
    );

    panel.innerHTML = `
        <div class="operational-timeline-header">
            <div class="operational-timeline-heading">
                Operational Timeline
            </div>

            <div class="operational-timeline-controls">
                <span
                    id="operational-timeline-count"
                    class="operational-timeline-count"
                >
                    0
                </span>

                <button
                    id="operational-timeline-toggle"
                    class="operational-timeline-toggle"
                    type="button"
                    title="Collapse timeline"
                >
                    -
                </button>
            </div>
        </div>

        <div
            id="operational-timeline-body"
            class="operational-timeline-body"
        >
            <div class="timeline-empty">
                Loading operational timeline...
            </div>
        </div>
    `;

    document.body.appendChild(
        panel
    );

    const toggleButton = document.getElementById(
        "operational-timeline-toggle"
    );

    if (toggleButton) {
        toggleButton.addEventListener(
            "click",
            toggleOperationalTimeline
        );
    }

    return panel;
}


function toggleOperationalTimeline() {
    const panel = document.getElementById(
        "operational-timeline-panel"
    );

    const button = document.getElementById(
        "operational-timeline-toggle"
    );

    if (!panel || !button) {
        return;
    }

    timelineCollapsed = !timelineCollapsed;

    panel.classList.toggle(
        "collapsed",
        timelineCollapsed
    );

    button.textContent = (
        timelineCollapsed
            ? "+"
            : "-"
    );

    button.title = (
        timelineCollapsed
            ? "Expand timeline"
            : "Collapse timeline"
    );
}


function formatTimelineElapsed(
    timestampSeconds
) {
    const totalSeconds = Math.max(
        0,
        Math.floor(
            Number(timestampSeconds)
        )
    );

    const minutes = Math.floor(
        totalSeconds / 60
    );

    const seconds = (
        totalSeconds % 60
    );

    return (
        `${String(minutes).padStart(2, "0")}:`
        + `${String(seconds).padStart(2, "0")}`
    );
}


function formatTimelineType(
    entryType
) {
    return entryType
        .replaceAll("_", " ")
        .replace(
            /\b\w/g,
            (letter) => letter.toUpperCase()
        );
}


function escapeTimelineHtml(value) {
    const element = document.createElement(
        "div"
    );

    element.textContent = (
        value == null
            ? ""
            : String(value)
    );

    return element.innerHTML;
}


function focusTimelinePosition(entry) {
    if (
        typeof map === "undefined"
        || typeof L === "undefined"
        || entry.latitude == null
        || entry.longitude == null
    ) {
        return;
    }

    const position = [
        entry.latitude,
        entry.longitude,
    ];

    map.setView(
        position,
        Math.max(
            map.getZoom(),
            15
        ),
        {
            animate: true,
        }
    );

    if (timelineFocusMarker) {
        map.removeLayer(
            timelineFocusMarker
        );
    }

    timelineFocusMarker = L.circleMarker(
        position,
        {
            radius: 10,
            color: "#ffffff",
            fillColor: "#38bdf8",
            fillOpacity: 0.9,
            weight: 3,
        }
    ).addTo(map);

    timelineFocusMarker.bindPopup(
        `
            <strong>
                ${escapeTimelineHtml(entry.title)}
            </strong>

            <br>

            ${escapeTimelineHtml(entry.message)}
        `
    );

    timelineFocusMarker.openPopup();

    setTimeout(
        () => {
            if (
                timelineFocusMarker
                && map.hasLayer(
                    timelineFocusMarker
                )
            ) {
                map.removeLayer(
                    timelineFocusMarker
                );

                timelineFocusMarker = null;
            }
        },
        6000
    );
}


function renderOperationalTimeline(
    timeline
) {
    const body = document.getElementById(
        "operational-timeline-body"
    );

    const count = document.getElementById(
        "operational-timeline-count"
    );

    if (!body || !count) {
        return;
    }

    const entries = Array.isArray(
        timeline.entries
    )
        ? [...timeline.entries]
        : [];

    count.textContent = String(
        timeline.total_entries ?? entries.length
    );

    if (entries.length === 0) {
        body.innerHTML = `
            <div class="timeline-empty">
                No operational events recorded.
            </div>
        `;

        return;
    }

    entries.reverse();

    const newestId = entries[0].id;

    body.innerHTML = entries.map(
        (entry, index) => {
            const hasPosition = (
                entry.latitude != null
                && entry.longitude != null
            );

            const isNew = (
                index === 0
                && lastTimelineEntryId !== null
                && newestId !== lastTimelineEntryId
            );

            const tags = [];

            tags.push(
                formatTimelineType(
                    entry.entry_type
                )
            );

            if (entry.asset_name) {
                tags.push(
                    entry.asset_name
                );
            }

            if (entry.related_event_id) {
                tags.push(
                    entry.related_event_id
                );
            }

            if (entry.mission_status) {
                tags.push(
                    entry.mission_status.replaceAll(
                        "_",
                        " "
                    )
                );
            }

            return `
                <article
                    class="
                        timeline-entry
                        severity-${escapeTimelineHtml(
                            entry.severity
                        )}
                        ${
                            hasPosition
                                ? "has-position"
                                : ""
                        }
                        ${
                            isNew
                                ? "timeline-entry-new"
                                : ""
                        }
                    "
                    data-entry-id="${escapeTimelineHtml(
                        entry.id
                    )}"
                >
                    <div class="timeline-entry-header">
                        <div class="timeline-entry-title">
                            ${escapeTimelineHtml(
                                entry.title
                            )}
                        </div>

                        <div class="timeline-entry-time">
                            +${formatTimelineElapsed(
                                entry.timestamp_seconds
                            )}
                        </div>
                    </div>

                    <div class="timeline-entry-message">
                        ${escapeTimelineHtml(
                            entry.message
                        )}
                    </div>

                    <div class="timeline-entry-meta">
                        ${tags.map(
                            (tag) => `
                                <span class="timeline-tag">
                                    ${escapeTimelineHtml(tag)}
                                </span>
                            `
                        ).join("")}
                    </div>

                    ${
                        hasPosition
                            ? `
                                <div class="timeline-position-hint">
                                    Click to locate on map
                                </div>
                            `
                            : ""
                    }
                </article>
            `;
        }
    ).join("");

    entries.forEach(
        (entry) => {
            if (
                entry.latitude == null
                || entry.longitude == null
            ) {
                return;
            }

            const element = body.querySelector(
                `[data-entry-id="${CSS.escape(
                    entry.id
                )}"]`
            );

            if (element) {
                element.addEventListener(
                    "click",
                    () => {
                        focusTimelinePosition(
                            entry
                        );
                    }
                );
            }
        }
    );

    lastTimelineEntryId = newestId;
}


async function refreshOperationalTimeline() {
    try {
        const response = await fetch(
            "/operational-timeline",
            {
                cache: "no-store",
            }
        );

        if (!response.ok) {
            throw new Error(
                `HTTP error: ${response.status}`
            );
        }

        const timeline = await response.json();

        renderOperationalTimeline(
            timeline
        );
    } catch (error) {
        console.error(
            "Unable to update operational timeline:",
            error
        );
    }
}


injectOperationalTimelineStyles();
createOperationalTimelinePanel();
refreshOperationalTimeline();

setInterval(
    refreshOperationalTimeline,
    3000
);