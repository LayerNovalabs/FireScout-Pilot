# FireScout Platform

FireScout is an emergency coordination project designed to simulate operations involving drones, sensors, and rescue vehicles.

The application includes two main scenarios:

- Wildfire response.
- Maritime search and rescue.

From the Command Center, users can view assets on a map, start missions, check detections, and follow the progress of each operation.

## Live Demo

https://fire-scout-platform.onrender.com/command-center

The application is hosted on Render using the free plan, so the first load may take a few seconds.

## How It Works

In the maritime scenario, a drone follows an automated search route. When its sensors confirm the location of a person, the rescue boat changes its destination and moves toward the detected coordinates.

In the wildfire scenario, the platform displays incidents, calculates priority search areas, and tracks the drones assigned to each mission.

## Main Features

- Interactive map.
- Drone and rescue boat simulation.
- Automated search route planning.
- Simulated victim detection.
- Battery, speed, and position tracking.
- Operational recommendations.
- Event timeline.
- Full simulation reset.

## Technologies

- Python
- FastAPI
- Pydantic
- HTML
- CSS
- JavaScript
- Leaflet
- Render

## Run Locally

Clone the repository:

```bash
git clone https://github.com/LayerNovalabs/Fire-Scout-Platform.git
cd Fire-Scout-Platform