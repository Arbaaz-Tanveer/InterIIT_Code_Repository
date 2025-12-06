from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess, OpaqueFunction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import subprocess
import os


def check_port(context, *args, **kwargs):
    # Check if port 9090 is in use
    result = subprocess.run(
        ["bash", "-c", "lsof -i :9090"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if result.stdout.strip():  # If output exists → port is busy
        print("\n\033[91mERROR: Port 9090 is already in use!\033[0m")
        print("\033[93mPlease free the port manually using:\033[0m")
        print("\033[96m  sudo fuser -k 9090/tcp\033[0m\n")
        print("Aborting launch...\n")
        raise SystemExit(1)  # Stop launch

    print("\033[92mPort 9090 is free. Launching rosbridge...\033[0m\n")


def generate_launch_description():

    # Run the check *before* launching nodes
    port_check = OpaqueFunction(function=check_port)

    # Path to the RPLIDAR package launch file
    rplidar_pkg_dir = get_package_share_directory('rplidar_ros')
    rplidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(rplidar_pkg_dir, 'launch', 'rplidar_a1_launch.py')
        ),
        launch_arguments={
            'serial_port': '/dev/ttyUSB0',
            'serial_baudrate': '115200',
            'frame_id': 'laser'
        }.items()
    )

    return LaunchDescription([
        port_check,

        # RPLIDAR A1 Launcher
        rplidar_launch,

        Node(
            package="rosbridge_server",
            executable="rosbridge_websocket",
            output="screen",
            parameters=[{"address": "0.0.0.0"}]
        ),

        Node(
            package="mpc_pkg",
            executable="controller1",
            output="screen",
            arguments=["--ros-args", "--log-level", "fatal"]
        ),

        Node(
            package="localisation_pkg",
            executable="geneticLocaliserServer",
            output="screen"
        ),

        Node(
            package="main_pkg",
            executable="path_planner",
            output="screen"
        ),

        Node(
            package="main_pkg",
            executable="main",
            output="screen"
        ),

        Node(
            package="main_pkg",
            executable="vision",
            output="screen"
        ),

        Node(
            package="main_pkg",
            executable="hardware",
            output="screen"
        ),

    ])
