import os
import subprocess
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, OpaqueFunction, RegisterEventHandler, ExecuteProcess
from launch.event_handlers import OnShutdown
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

def check_port(context, *args, **kwargs):
    # Check if port 9090 is in use
    result = subprocess.run(
        ["bash", "-c", "lsof -i :9090"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if result.stdout.strip():  # If output exists -> port is busy
        print("\n\033[91mERROR: Port 9090 is already in use!\033[0m")
        print("\033[93mPlease free the port manually using:\033[0m")
        print("\033[96m  sudo fuser -k 9090/tcp\033[0m\n")
        print("Aborting launch...\n")
        raise SystemExit(1)  # Stop launch

    print("\033[92mPort 9090 is free. Launching rosbridge...\033[0m\n")

def generate_launch_description():

    pkg_bringup = get_package_share_directory('slam')
    pkg_slam = get_package_share_directory('slam_toolbox')
    pkg_rplidar = get_package_share_directory('rplidar_ros')

    # Run the check *before* launching nodes
    port_check = OpaqueFunction(function=check_port)

    # 1. Localization (your file)
    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_bringup, 'launch', 'localization.launch.py')
        )
    )

    # 2. SLAM Toolbox online_async
    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_bringup, 'launch', 'online_async_launch.py')
        )
    )

    # 3. RPLIDAR A1 driver
    rplidar = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_bringup, 'launch', 'rplidar_a1_launch.py')
        )
    )
    
    rviz_config_path=os.path.join(pkg_bringup, 'rviz', 'my_robot.rviz')
    rviz=Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_path]
    )
    scan_filter = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        name='scan_filter',
        parameters=[
            {'filter_chain_parameter_name': 'laser_scan_filter_chain'},
            os.path.join(pkg_bringup, 'config', 'scan_filters.yaml')
        ],
        remappings=[
            ('scan', '/scan'),                  # input from lidar
            ('scan_filtered', '/scan_filtered') # output of filter
        ]
    )

    hardware_node = Node(
        package='warehouse_robot_bringup',
        executable='hardware',
        name='hardware',
        output='screen'
    )

    rosbridge_node = Node(
        package='rosbridge_server',
        executable='rosbridge_websocket',
        name='rosbridge_websocket',
        output='screen',
        parameters=[{'address': '0.0.0.0'}]
    )

    keyboard_map_saver = Node(
        package='slam',
        executable='keyboard_map_saver',
        name='keyboard_map_saver',
        output='screen',
        prefix='gnome-terminal --'
    )



    return LaunchDescription([
        port_check,
        rplidar,
        scan_filter,
        localization,
        slam,
        rviz,
        hardware_node,
        rosbridge_node,
        keyboard_map_saver,
    ])
