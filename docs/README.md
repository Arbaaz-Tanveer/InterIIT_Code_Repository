# Warehouse Robot Repository

This repository contains the code for the Warehouse Robot, organized into ROS2 packages.

## Structure

- **src/warehouse_robot_bringup**: Launch files and top-level scripts for bringing up the robot.
- **src/warehouse_navigation**: SLAM, path planning, and navigation logic.
- **src/warehouse_scanning**: QR code detection and camera control.
- **src/warehouse_hmi**: Dashboard and control interfaces.
- **src/warehouse_msgs**: Custom ROS2 message and service definitions.

## Setup Guide

### Prerequisites

- ROS2 Humble (or compatible version)
- Python 3.10+
- OpenCV
- Ultralytics YOLO

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd InterIIT_Code_Repository
    ```

2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Build the workspace:**
    ```bash
    colcon build
    ```

4.  **Source the setup script:**
    ```bash
    source install/setup.bash
    ```

## Usage

### Simulation

To run the simulation with the full system:

```bash
ros2 launch warehouse_robot_bringup simulation.launch.py
```

### Real Robot

To run the system on the real robot:

```bash
ros2 launch warehouse_robot_bringup system.launch.py
```

## Packages

### warehouse_navigation

Contains the `genetic_node` (C++) and python scripts for path planning (`path_planner.py`), obstacle detection (`obstacle_detector.py`), and vision utilities.

### warehouse_scanning

Contains the `camera_node` for QR code detection using YOLO.

### warehouse_hmi

Contains the `target_gui` for setting goals and `keyboard_controller` for manual control.
