(() => {
    const SECTION_ID = (
        "command-center-bottom-section"
    );

    const CONTAINER_ID = (
        "command-center-bottom-panels"
    );

    const PANEL_IDS = [
        "sensor-detection-panel",
        "operational-timeline-panel",
    ];


    function injectLayoutStyles() {
        if (
            document.getElementById(
                "command-center-panel-layout-styles"
            )
        ) {
            return;
        }

        const style = document.createElement(
            "style"
        );

        style.id = (
            "command-center-panel-layout-styles"
        );

        style.textContent = `
            #command-center-bottom-section {
                position: relative !important;
                display: block !important;
                width: calc(100% - 32px) !important;
                max-width: 1400px !important;
                margin: 28px auto 50px !important;
                padding: 18px !important;
                box-sizing: border-box !important;
                border: 1px solid rgba(148, 163, 184, 0.24);
                border-radius: 14px;
                background: rgba(15, 23, 42, 0.78);
                z-index: auto !important;
            }

            .command-center-bottom-heading {
                margin: 0 0 16px !important;
                color: #e2e8f0;
                font-size: 15px;
                font-weight: 800;
                letter-spacing: 0.06em;
                text-transform: uppercase;
            }

            #command-center-bottom-panels {
                position: relative !important;
                display: grid !important;
                grid-template-columns:
                    minmax(0, 1fr)
                    minmax(0, 1fr);
                align-items: start;
                gap: 18px;
                width: 100%;
            }

            #command-center-bottom-panels
            #sensor-detection-panel,
            #command-center-bottom-panels
            #operational-timeline-panel {
                position: relative !important;
                inset: auto !important;
                top: auto !important;
                right: auto !important;
                bottom: auto !important;
                left: auto !important;

                display: flex !important;
                width: 100% !important;
                min-width: 0 !important;
                max-width: none !important;
                height: auto !important;
                max-height: none !important;

                margin: 0 !important;
                box-sizing: border-box !important;
                z-index: auto !important;
                transform: none !important;
            }

            #command-center-bottom-panels
            #sensor-detection-panel {
                order: 1;
            }

            #command-center-bottom-panels
            #operational-timeline-panel {
                order: 2;
            }

            #command-center-bottom-panels
            #sensor-status-list {
                max-height: 520px;
                overflow-y: auto;
            }

            #command-center-bottom-panels
            .operational-timeline-body {
                display: block;
                max-height: 520px;
                overflow-y: auto;
            }

            #command-center-bottom-panels
            .operational-timeline-panel.collapsed
            .operational-timeline-body {
                display: none;
            }

            @media (max-width: 1000px) {
                #command-center-bottom-panels {
                    grid-template-columns:
                        minmax(0, 1fr) !important;
                }
            }

            @media (max-width: 600px) {
                #command-center-bottom-section {
                    width: calc(100% - 20px) !important;
                    margin: 18px auto 30px !important;
                    padding: 10px !important;
                }
            }
        `;

        document.head.appendChild(
            style
        );
    }


    function createBottomSection() {
        let section = document.getElementById(
            SECTION_ID
        );

        if (section) {
            return section;
        }

        section = document.createElement(
            "section"
        );

        section.id = SECTION_ID;

        section.innerHTML = `
            <h2 class="command-center-bottom-heading">
                Operational Intelligence
            </h2>

            <div id="${CONTAINER_ID}"></div>
        `;

        /*
         * Se coloca dentro del contenido principal,
         * al final de todos los paneles existentes.
         */
        const main = document.querySelector(
            "main"
        );

        if (main) {
            main.appendChild(
                section
            );

            return section;
        }

        const firstScript = (
            document.body.querySelector(
                "script"
            )
        );

        if (firstScript) {
            document.body.insertBefore(
                section,
                firstScript
            );
        } else {
            document.body.appendChild(
                section
            );
        }

        return section;
    }


    function forceNormalPosition(panel) {
        panel.style.setProperty(
            "position",
            "relative",
            "important"
        );

        panel.style.setProperty(
            "top",
            "auto",
            "important"
        );

        panel.style.setProperty(
            "right",
            "auto",
            "important"
        );

        panel.style.setProperty(
            "bottom",
            "auto",
            "important"
        );

        panel.style.setProperty(
            "left",
            "auto",
            "important"
        );

        panel.style.setProperty(
            "width",
            "100%",
            "important"
        );

        panel.style.setProperty(
            "max-height",
            "none",
            "important"
        );

        panel.style.setProperty(
            "z-index",
            "auto",
            "important"
        );

        panel.style.setProperty(
            "transform",
            "none",
            "important"
        );
    }


    function relocatePanels() {
        createBottomSection();

        const container = document.getElementById(
            CONTAINER_ID
        );

        if (!container) {
            return;
        }

        PANEL_IDS.forEach(
            (panelId) => {
                const panel = document.getElementById(
                    panelId
                );

                if (!panel) {
                    return;
                }

                forceNormalPosition(
                    panel
                );

                if (
                    panel.parentElement
                    !== container
                ) {
                    container.appendChild(
                        panel
                    );
                }
            }
        );
    }


    function initializePanelLayout() {
        injectLayoutStyles();
        createBottomSection();
        relocatePanels();

        /*
         * Detecta paneles creados después de cargar
         * este archivo y los mueve automáticamente.
         */
        const observer = new MutationObserver(
            () => {
                relocatePanels();
            }
        );

        observer.observe(
            document.body,
            {
                childList: true,
                subtree: true,
            }
        );

        /*
         * Comprobación adicional por si otro script
         * vuelve a modificar los paneles.
         */
        setInterval(
            relocatePanels,
            1000
        );
    }


    if (
        document.readyState === "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            initializePanelLayout
        );
    } else {
        initializePanelLayout();
    }
})();