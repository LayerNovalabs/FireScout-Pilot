# FireScout Architecture

## 1. Architecture Goal

FireScout is designed as a modular, hardware-independent Emergency Intelligence Platform.

The platform must support both simulated and real devices through the same core interfaces.

The initial competition version will use simulated devices, while future production versions will connect to real hardware without requiring a complete redesign of the platform.

## 2. High-Level Architecture

FireScout is divided into five main platform areas:

### Core Platform

Responsible for shared platform services such as:

- Configuration
- Events
- User management
- Permissions
- Logging
- System health

### Device Management

Responsible for connecting and managing operational assets.

Supported asset types may include:

- Aerial drones
- Ground robots
- Maritime vehicles
- Fixed sensors
- Cameras
- IoT devices
- Simulated devices

### Mission Engine

Responsible for managing operational missions.

Examples:

- Wildfire
- Flood
- Maritime Search and Rescue
- Missing Person
- Hazmat

### Intelligence Engine

Responsible for processing operational data and generating analysis.

Future capabilities may include:

- Fire detection
- Smoke detection
- Victim detection
- Risk analysis
- Route recommendations
- Decision support

### Command Center

The user-facing operational interface.

It may include:

- Live map
- Device status
- Telemetry
- Alerts
- Mission controls
- Recommendations
- Mission replay
- Reports

## 3. Core Architectural Principle

FireScout must not depend directly on a specific hardware manufacturer.

The platform should interact with device capabilities instead of hardcoded brands.

For example:

```python
device.supports_video
device.supports_gps
device.supports_thermal_camera
```

instead of:
```python
if device.brand == "DJI":
```

## 4. Asset Abstraction

Every connected system is represented as an Asset.

An Asset may be:

- Drone
- Robot
- Boat
- Camera
- Sensor
- Simulator

All Assets should expose a normalized interface to the rest of FireScout.

The rest of the platform should not need to know whether telemetry comes from a simulator or a real device.

## 5. Adapter Architecture

External systems connect to FireScout through adapters.

Examples:

- Simulator Adapter
- DJI Adapter
- MAVLink Adapter
- PX4 Adapter
- IoT Adapter

Each adapter translates external data into FireScout's internal data model.

## 6. Simulation-First Principle

The simulator is a first-class platform component.

It will be used for:

- Competition demonstrations
- Testing
- Development
- Training
- Reproducing incidents
- Validating new mission logic

The same mission and user interface layers should work with both simulated and real devices.

## 7. Initial Competition Architecture

The first version will prioritize:

- Simulator Adapter
- Asset Management
- Mission Engine
- Operational Events
- Command Center
- Decision Recommendations
- Mission Reports

Real hardware integrations will be added later through new adapters.

## 8. Future Scalability

The architecture should allow future expansion without rewriting the core platform.

Possible future additions include:

- Real-time multi-agency operations
- Cloud deployment
- Edge processing
- AI model plugins
- Mission plugins
- Third-party integrations
- Fleet management
- Developer SDK